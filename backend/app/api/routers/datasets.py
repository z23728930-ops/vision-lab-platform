# app/api/routers/datasets.py

import zipfile
import os
import shutil
import time
import mimetypes  # <-- 新增导入 mimetypes
import json
import random
from pathlib import Path
from typing import List, Any, Optional, Annotated
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ... import crud, schemas
from ...core.config import settings
from ...db import models
from ...db.base import get_db
from ..deps import get_current_active_user

import imghdr
from PIL import Image as PILImage
from ...crud.crud_image import crud_image
from ...services.annotation_exporter import annotation_exporter
from ...services.training_package_exporter import create_yolo_training_package

router = APIRouter()


class PublicStatusUpdate(BaseModel):
    is_public: bool


class DatasetSplitRequest(BaseModel):
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    seed: int = 42


class AnnotationReviewUpdate(BaseModel):
    reviewed: bool = True


class DatasetCloneRequest(BaseModel):
    name: Optional[str] = None


@router.get("/{dataset_id}/readiness-check", tags=["Datasets"])
def check_dataset_readiness(
        dataset_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and not dataset.is_public and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions.")

    dataset_path = Path(dataset.storage_path)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset_path
    supported_extensions = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
    valid_count = 0
    damaged_files = []
    unsupported_files = []
    formats = set()
    for image in dataset.images or []:
        image_path = Path(image.file_path)
        if not image_path.is_absolute():
            image_path = Path.cwd() / image_path
        extension = image_path.suffix.lower()
        if extension not in supported_extensions:
            unsupported_files.append(image.filename)
            continue
        try:
            with PILImage.open(image_path) as opened_image:
                opened_image.verify()
            valid_count += 1
            formats.add(extension.lstrip(".").upper())
        except Exception:
            damaged_files.append(image.filename)

    dataset_name = dataset.name.lower()
    if dataset_name == "qk" or dataset_name.startswith("qk_"):
        recommended_name = "qk"
    elif dataset_name == "coco_for_yolov8n" or dataset_name.startswith("coco_for_yolov8n_"):
        recommended_name = "yolo8n"
    elif dataset_name == "test_312" or dataset_name.startswith("test_312_"):
        recommended_name = "my-test-unet"
    else:
        recommended_name = None
    recommended_model = None
    if recommended_name:
        recommended_model = db.query(models.Model).filter(
            models.Model.name == recommended_name,
            models.Model.is_deleted == False,
        ).first()
    model_path = None
    model_file_exists = False
    if recommended_model:
        model_path = Path(recommended_model.file_path)
        if not model_path.is_absolute():
            model_path = Path.cwd() / model_path
        model_file_exists = model_path.exists()

    checks = [
        {"key": "directory", "label": "数据目录存在", "passed": dataset_path.exists(), "detail": str(dataset_path)},
        {"key": "images", "label": "存在可检测图片", "passed": valid_count > 0, "detail": f"有效图片 {valid_count} 张"},
        {"key": "format", "label": "图片格式受支持", "passed": not unsupported_files, "detail": "、".join(sorted(formats)) or "未识别"},
        {"key": "integrity", "label": "图片文件可正常读取", "passed": not damaged_files, "detail": f"损坏图片 {len(damaged_files)} 张"},
        {"key": "model", "label": "推荐模型已匹配", "passed": recommended_model is not None, "detail": recommended_name or "暂无明确推荐模型"},
        {"key": "model_file", "label": "推荐模型文件可用", "passed": model_file_exists, "detail": "文件存在" if model_file_exists else "模型文件缺失或未匹配"},
    ]
    ready = all(item["passed"] for item in checks)
    return {
        "dataset": {"id": dataset.id, "name": dataset.name, "image_count": len(dataset.images or []), "owner": dataset.owner.username if dataset.owner else None, "is_public": dataset.is_public},
        "valid_image_count": valid_count,
        "damaged_count": len(damaged_files),
        "damaged_files": damaged_files[:10],
        "unsupported_count": len(unsupported_files),
        "formats": sorted(formats),
        "recommended_model": ({"id": recommended_model.id, "name": recommended_model.name, "model_type": recommended_model.model_type, "file_exists": model_file_exists} if recommended_model else None),
        "permission": "公共只读" if dataset.owner_id != current_user.id else "本人数据集",
        "checks": checks,
        "ready": ready,
    }


@router.post("/{dataset_id}/clone", response_model=schemas.Dataset, status_code=status.HTTP_201_CREATED, tags=["Datasets"])
def clone_dataset(
        dataset_id: int,
        clone_in: DatasetCloneRequest,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    source = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if source.owner_id != current_user.id and not source.is_public and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions to copy this dataset.")
    if source.owner_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该数据集已经属于当前账号，无需复制。")

    source_path = Path(source.storage_path)
    if not source_path.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "源数据集目录不存在。")
    clone_name = (clone_in.name or f"{source.name}_{current_user.username}").strip()
    target_root = Path(settings.UPLOADS_DIR) / "datasets" / str(current_user.id)
    target_path = target_root / f"{clone_name.replace(' ', '_')}_{int(time.time())}"
    target_root.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns(".dataset_split.json", ".annotation_review.json"))
        new_dataset = crud.crud_dataset.create_dataset(
            db,
            dataset=schemas.DatasetCreate(name=clone_name, description=f"复制自公共数据集：{source.name}", is_public=False),
            owner_id=current_user.id,
            storage_path=str(target_path),
        )
        image_records = []
        for source_image in source.images or []:
            try:
                relative_path = Path(source_image.file_path).relative_to(source_path)
            except ValueError:
                relative_path = Path(source_image.filename)
            copied_path = target_path / relative_path
            if copied_path.exists():
                image_records.append(schemas.ImageCreate(dataset_id=new_dataset.id, file_path=str(copied_path), filename=source_image.filename))
        if image_records:
            crud_image.create_multiple_images(db, image_records)
        db.refresh(new_dataset)
        return new_dataset
    except Exception as error:
        if target_path.exists():
            shutil.rmtree(target_path, ignore_errors=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"复制数据集失败：{error}")


def _split_manifest_path(dataset: models.Dataset) -> Path:
    return Path(dataset.storage_path) / ".dataset_split.json"


def _annotation_review_path(dataset: models.Dataset) -> Path:
    return Path(dataset.storage_path) / ".annotation_review.json"


def _read_reviewed_ids(dataset: models.Dataset) -> set[int]:
    review_path = _annotation_review_path(dataset)
    if not review_path.exists():
        return set()
    try:
        with review_path.open("r", encoding="utf-8") as review_file:
            return {int(image_id) for image_id in json.load(review_file).get("reviewed_image_ids", [])}
    except (ValueError, TypeError, json.JSONDecodeError):
        return set()


def _annotation_stats(dataset: models.Dataset) -> dict:
    images = list(dataset.images or [])
    annotated_ids = {image.id for image in images if image.annotations}
    reviewed_ids = _read_reviewed_ids(dataset) | annotated_ids
    valid_ids = {image.id for image in images}
    reviewed_ids &= valid_ids
    total = len(images)
    reviewed = len(reviewed_ids)
    return {
        "annotated_image_count": len(annotated_ids),
        "reviewed_image_count": reviewed,
        "unreviewed_image_count": total - reviewed,
        "annotation_progress": round(reviewed * 100 / total, 1) if total else 0.0,
    }


@router.get("/{dataset_id}/annotation-status", tags=["Datasets"])
def get_annotation_status(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and not dataset.is_public and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions.")
    return {"dataset_id": dataset.id, "image_count": len(dataset.images or []), **_annotation_stats(dataset)}


@router.post("/{dataset_id}/images/{image_id}/review", tags=["Datasets"])
def update_image_review(dataset_id: int, image_id: int, review_in: AnnotationReviewUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the dataset owner can review annotations.")
    image_ids = {image.id for image in dataset.images or []}
    if image_id not in image_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found in this dataset.")
    reviewed_ids = _read_reviewed_ids(dataset)
    if review_in.reviewed:
        reviewed_ids.add(image_id)
    else:
        reviewed_ids.discard(image_id)
    with _annotation_review_path(dataset).open("w", encoding="utf-8") as review_file:
        json.dump({"reviewed_image_ids": sorted(reviewed_ids)}, review_file, ensure_ascii=False, indent=2)
    return {"dataset_id": dataset_id, "image_id": image_id, "reviewed": review_in.reviewed, **_annotation_stats(dataset)}


@router.get("/{dataset_id}/split", tags=["Datasets"])
def get_dataset_split(dataset_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions.")
    manifest_path = _split_manifest_path(dataset)
    if not manifest_path.exists():
        return {"configured": False, "dataset_id": dataset_id}
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        return {"configured": True, **json.load(manifest_file)}


@router.post("/{dataset_id}/split", tags=["Datasets"])
def split_dataset(dataset_id: int, split_in: DatasetSplitRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the dataset owner can split this dataset.")
    ratios = (split_in.train_ratio, split_in.val_ratio, split_in.test_ratio)
    if any(ratio < 0 or ratio > 1 for ratio in ratios) or abs(sum(ratios) - 1.0) > 0.0001:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "训练集、验证集和测试集比例之和必须等于 100%。")
    if split_in.train_ratio <= 0 or split_in.test_ratio <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "训练集和测试集比例必须大于 0。")
    images = crud_image.get_images_by_dataset(db, dataset_id=dataset_id)
    if len(images) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "数据集至少需要 3 张图片才能划分。")
    shuffled = list(images)
    random.Random(split_in.seed).shuffle(shuffled)
    total = len(shuffled)
    train_count = max(1, int(total * split_in.train_ratio))
    val_count = int(total * split_in.val_ratio)
    test_count = total - train_count - val_count
    if test_count < 1:
        test_count = 1
        train_count = total - val_count - test_count

    def serialize(image):
        try:
            relative_path = Path(image.file_path).relative_to(Path(dataset.storage_path)).as_posix()
        except ValueError:
            relative_path = image.filename
        return {"id": image.id, "filename": image.filename, "relative_path": relative_path}

    train_end = train_count
    val_end = train_count + val_count
    manifest = {
        "dataset_id": dataset.id, "dataset_name": dataset.name, "seed": split_in.seed,
        "ratios": {"train": split_in.train_ratio, "val": split_in.val_ratio, "test": split_in.test_ratio},
        "counts": {"total": total, "train": train_count, "val": val_count, "test": test_count},
        "splits": {
            "train": [serialize(image) for image in shuffled[:train_end]],
            "val": [serialize(image) for image in shuffled[train_end:val_end]],
            "test": [serialize(image) for image in shuffled[val_end:]],
        },
    }
    manifest_path = _split_manifest_path(dataset)
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
    return {"configured": True, **manifest}


@router.patch("/{dataset_id}/public", response_model=schemas.Dataset)
def update_public_status(
        dataset_id: int,
        status_update: PublicStatusUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions.")

    return crud.crud_dataset.update_dataset_public_status(db, dataset_id=dataset_id, is_public=status_update.is_public)


def unzip_file(zip_src: Path, dst_dir: Path) -> List[Path]:
    """
    健壮的解压函数，能处理中文文件名乱码问题。
    如果解压失败，会直接抛出异常，由调用者处理清理。
    返回解压后的所有图片文件的绝对路径列表。
    """
    extracted_image_paths = []
    supported_image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    with zipfile.ZipFile(zip_src, 'r') as zf:
        for member in zf.infolist():
            # 路径遍历攻击防护：确保文件名不包含 '..' 或绝对路径
            if ".." in member.filename or member.filename.startswith("/") or member.filename.startswith("\\"):
                raise ValueError(f"ZIP文件包含无效或危险的路径: {member.filename}")

            target_name = None
            # 尝试多种编码解码文件名，处理中文乱码
            if member.flag_bits & 0x800:  # UTF-8 编码标志
                target_name = member.filename
            else:
                try:
                    target_name = member.filename.encode('cp437').decode('utf-8')
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        target_name = member.filename.encode('cp437').decode('gbk')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        print(
                            f"Warning: Could not decode filename '{member.filename}' using UTF-8 or GBK. Using original.")
                        target_name = member.filename

            if not target_name:
                continue

            target_path = dst_dir / target_name
            # 确保目标路径在预期的解压目录下
            if not target_path.is_relative_to(dst_dir):
                raise ValueError(f"Attempted path traversal detected: {target_path}")

            target_path.parent.mkdir(parents=True, exist_ok=True)  # 确保子目录存在

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                # 临时保存文件到磁盘，以便 imghdr 检查
                temp_file_path = target_path.with_suffix(target_path.suffix + ".tmp_check")
                try:
                    with zf.open(member, 'r') as source, open(temp_file_path, 'wb') as target:
                        shutil.copyfileobj(source, target)

                    if target_path.suffix.lower() in supported_image_extensions:
                        if imghdr.what(str(temp_file_path)):  # imghdr 需要字符串路径
                            os.rename(temp_file_path, target_path)
                            extracted_image_paths.append(target_path)
                        else:
                            print(
                                f"Warning: File {target_name} has image extension but is not a valid image. Skipping.")
                            os.remove(temp_file_path)  # 删除无效图片临时文件
                    else:
                        # 标签、类别配置和数据说明也是训练数据的一部分，必须原样保留。
                        os.replace(temp_file_path, target_path)
                        print(f"Info: Preserved dataset metadata file: {target_name}")
                except Exception as e:
                    print(f"Error processing file {target_name}: {e}")
                    if temp_file_path.exists():
                        os.remove(temp_file_path)
                    continue
    return extracted_image_paths


@router.post("/upload", response_model=schemas.Dataset, status_code=status.HTTP_201_CREATED)
def upload_dataset(
        *,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        name: str = Form(...),
        description: Optional[str] = Form(""),
        is_public: bool = Form(False),
        file: UploadFile = File(...)
) -> Any:
    """
    上传一个新的数据集。文件必须是 .zip 格式。
    解压后，会自动识别并记录数据集中的图片文件。
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip is accepted.")

    dataset_folder_name = f"{name.replace(' ', '_')}_{int(time.time())}"
    user_datasets_base_path = Path(settings.UPLOADS_DIR) / "datasets" / str(current_user.id)
    storage_path = user_datasets_base_path / dataset_folder_name

    # 路径安全检查：确保 storage_path 在允许的上传目录下
    if not storage_path.is_relative_to(user_datasets_base_path.parent):
        raise HTTPException(status_code=400, detail="Invalid target storage path for security reasons.")

    if storage_path.exists():
        try:
            shutil.rmtree(storage_path)
        except OSError as e:
            raise HTTPException(status_code=500,
                                detail=f"无法清理旧目录 '{storage_path}'。请手动删除或检查权限。错误: {e}")

    storage_path.mkdir(parents=True, exist_ok=True)

    zip_path = storage_path / file.filename

    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_image_paths = unzip_file(zip_path, storage_path)

        actual_storage_path = str(storage_path)
        # 优化：如果ZIP解压后只有一个顶层目录，且该目录包含图片，则将该目录作为数据集根目录
        extracted_contents = list(storage_path.iterdir())
        if len(extracted_contents) == 1 and extracted_contents[0].is_dir():
            # 检查子目录中是否有图片，避免将空目录或非图片目录设为实际路径
            # 使用 rglob('*') 递归查找所有文件
            sub_dir_has_images = any(f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'} for f in
                                     extracted_contents[0].rglob('*'))
            if sub_dir_has_images:
                actual_storage_path = str(extracted_contents[0])
            else:
                print(
                    f"Info: Single extracted subdirectory '{extracted_contents[0].name}' contains no images. Using original storage path.")

        dataset_in = schemas.DatasetCreate(name=name, description=description, is_public=is_public)
        new_dataset = crud.crud_dataset.create_dataset(db, dataset=dataset_in, owner_id=current_user.id,
                                                       storage_path=actual_storage_path)

        images_to_create = []
        base_path_for_relative = Path(actual_storage_path)
        for img_path in extracted_image_paths:
            try:
                # 确保 img_path 确实在 actual_storage_path 之下，防止记录外部文件
                if not img_path.is_relative_to(base_path_for_relative):
                    print(
                        f"Warning: Image {img_path} is outside expected dataset path {base_path_for_relative}. Skipping record.")
                    continue

                relative_img_path = img_path.relative_to(base_path_for_relative).as_posix()
                images_to_create.append(schemas.ImageCreate(
                    dataset_id=new_dataset.id,
                    file_path=str(img_path),  # 存储绝对路径
                    filename=img_path.name  # 存储原始文件名
                ))
            except ValueError:  # 如果 relative_to 失败，说明不在其下
                print(f"Warning: Image {img_path} is not relative to {base_path_for_relative}. Skipping image record.")
                continue

        if images_to_create:
            crud_image.create_multiple_images(db, images_to_create)
            print(f"Recorded {len(images_to_create)} images for dataset {new_dataset.id}.")
        else:
            print(f"No supported images found in dataset {new_dataset.id}.")

        return new_dataset

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的ZIP文件格式。")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"ZIP文件内容错误：{ve}")
    except HTTPException:  # 重新抛出 FastAPI 异常
        raise
    except Exception as e:
        print(f"数据集上传和处理失败。错误: {e}")
        import traceback
        traceback.print_exc()
        if storage_path.exists():
            try:
                shutil.rmtree(storage_path)
            except OSError as cleanup_e:
                print(f"清理失败 '{storage_path}': {cleanup_e}")
        raise HTTPException(status_code=500, detail=f"处理上传文件失败: {e}")
    finally:
        file.file.close()  # 确保关闭上传文件流
        if zip_path.exists():
            zip_path.unlink()  # 删除临时ZIP文件


@router.post("/upload_folder", response_model=schemas.Dataset, status_code=status.HTTP_201_CREATED, tags=["Datasets"])
async def upload_dataset_folder(
        *,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        name: str = Form(...),
        description: Optional[str] = Form(""),
        is_public: bool = Form(False),
        # 使用 Annotated 结合 List[UploadFile] 和 List[str] 来接收多个文件及其相对路径
        files: Annotated[List[UploadFile], File(description="Files from the uploaded folder")],
        relative_paths: Annotated[List[str], Form(description="Relative paths of the files within the folder")]
) -> Any:
    print("Received request for /upload_folder")
    """
    上传一个新的数据集文件夹。
    前端会发送文件夹中的所有文件及其相对路径。
    """
    if len(files) != len(relative_paths):
        raise HTTPException(status_code=400, detail="Number of files and relative paths do not match.")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for folder upload.")

    dataset_folder_name = f"{name.replace(' ', '_')}_{int(time.time())}"
    user_datasets_base_path = Path(settings.UPLOADS_DIR) / "datasets" / str(current_user.id)
    storage_path = user_datasets_base_path / dataset_folder_name

    # 路径安全检查：确保 storage_path 在允许的上传目录下
    if not storage_path.is_relative_to(user_datasets_base_path.parent):
        raise HTTPException(status_code=400, detail="Invalid target storage path for security reasons.")

    # 如果目标目录已存在（不应该发生，因为有时间戳），则先清理
    if storage_path.exists():
        try:
            shutil.rmtree(storage_path)
        except OSError as e:
            raise HTTPException(status_code=500,
                                detail=f"无法清理旧目录 '{storage_path}'。请手动删除或检查权限。错误: {e}")

    storage_path.mkdir(parents=True, exist_ok=True)  # 创建根目录

    uploaded_image_paths = []
    supported_image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    try:
        for i, file_obj in enumerate(files):
            relative_path_str = relative_paths[i]
            # 路径遍历攻击防护：确保相对路径不包含 '..' 或绝对路径
            if ".." in relative_path_str or relative_path_str.startswith("/") or relative_path_str.startswith("\\"):
                raise HTTPException(status_code=400, detail=f"Invalid or dangerous relative path: {relative_path_str}")

            # 构建完整的保存路径
            file_save_path = storage_path / relative_path_str
            # 再次检查文件最终保存路径是否在预期的 storage_path 之下
            if not file_save_path.is_relative_to(storage_path):
                raise HTTPException(status_code=400,
                                    detail=f"Attempted path traversal detected for file: {relative_path_str}")

            file_save_path.parent.mkdir(parents=True, exist_ok=True)  # 确保子目录存在

            # 保存文件
            try:
                with open(file_save_path, "wb") as buffer:
                    content = await file_obj.read()  # 使用 await file_obj.read() 读取文件内容
                    buffer.write(content)

                # 检查是否为图片文件
                if file_save_path.suffix.lower() in supported_image_extensions:
                    if imghdr.what(str(file_save_path)):  # imghdr 需要字符串路径
                        uploaded_image_paths.append(file_save_path)
                    else:
                        print(
                            f"Warning: File {file_obj.filename} has image extension but is not a valid image. Skipping image record.")
                else:
                    print(f"Info: Skipping non-image file record: {file_obj.filename}")

            except Exception as e:
                print(f"Error saving file {file_obj.filename}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to save file {file_obj.filename}: {e}")
            finally:
                await file_obj.close()  # 确保关闭上传文件流

        actual_storage_path = str(storage_path)

        # 3. 在数据库中创建 Dataset 记录
        dataset_in = schemas.DatasetCreate(name=name, description=description, is_public=is_public)
        new_dataset = crud.crud_dataset.create_dataset(db, dataset=dataset_in, owner_id=current_user.id,
                                                       storage_path=actual_storage_path)

        # 4. 遍历上传的图片路径，并为每张图片创建 Image 记录
        images_to_create_records = []
        base_path_for_relative = Path(actual_storage_path)
        for img_path in uploaded_image_paths:
            try:
                # 确保 img_path 是在 actual_storage_path 内部
                if not img_path.is_relative_to(base_path_for_relative):  # 更健壮的检查
                    print(
                        f"Warning: Image {img_path} is outside expected dataset path {base_path_for_relative}. Skipping record.")
                    continue

                relative_img_path = img_path.relative_to(base_path_for_relative).as_posix()
                images_to_create_records.append(schemas.ImageCreate(
                    dataset_id=new_dataset.id,
                    file_path=str(img_path),  # 存储绝对路径
                    filename=img_path.name  # 存储文件名
                ))
            except ValueError:
                print(f"Warning: Image {img_path} is not relative to {base_path_for_relative}. Skipping image record.")
                continue

        if images_to_create_records:
            crud_image.create_multiple_images(db, images_to_create_records)
            print(f"Recorded {len(images_to_create_records)} images for dataset {new_dataset.id}.")
        else:
            print(f"No supported images found in dataset {new_dataset.id}.")

        return new_dataset

    except HTTPException:  # 重新抛出 FastAPI 异常
        raise
    except Exception as e:
        print(f"数据集文件夹上传和处理失败。错误: {e}")
        import traceback
        traceback.print_exc()
        # 如果发生错误，清理可能已创建的部分目录
        if storage_path.exists():
            try:
                shutil.rmtree(storage_path)
            except OSError as cleanup_e:
                print(f"清理失败 '{storage_path}': {cleanup_e}")
        raise HTTPException(status_code=500, detail=f"处理上传文件夹失败: {e}")


@router.get("/", response_model=List[schemas.Dataset])
def read_datasets(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        include_public: Optional[bool] = False,
        skip: int = 0,
        limit: int = 100
) -> Any:
    """
    获取数据集列表。
    - 如果 `include_public` 为 `True`，则返回当前用户的数据集以及所有公开数据集（管理员可查看所有）。
    - 否则，只返回当前用户的数据集。
    """
    datasets = crud.crud_dataset.get_multi(
        db=db,
        user=current_user,
        include_public=include_public,
        skip=skip,
        limit=limit
    )
    result = []
    for d in datasets:
        path = Path(d.storage_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        count = len(d.images or [])
        result.append({"id": d.id, "name": d.name, "description": d.description, "is_public": d.is_public, "owner_id": d.owner_id, "storage_path": d.storage_path, "created_at": d.created_at, "owner": d.owner, "image_count": count, "path_exists": path.exists(), "ready_for_inference": path.exists() and count > 0, **_annotation_stats(d)})
    return result


@router.get("/{dataset_id}/download")
def download_dataset(
        dataset_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    下载指定的数据集 (压缩为zip)。
    """
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    # 权限检查：数据集所有者或公开数据集可下载
    if dataset.owner_id != current_user.id and not dataset.is_public:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    path_to_archive = Path(dataset.storage_path)

    temp_zip_name_base = Path(
        settings.UPLOADS_DIR) / f"temp_download_{dataset.name.replace(' ', '_')}_{int(time.time())}"

    temp_zip_name = shutil.make_archive(
        base_name=str(temp_zip_name_base),
        format='zip',
        root_dir=str(path_to_archive)
    )

    background_tasks.add_task(os.remove, temp_zip_name)

    return FileResponse(
        path=temp_zip_name,
        media_type='application/zip',
        filename=f"{dataset.name.replace(' ', '_')}.zip"
    )


# --- 修改：浏览数据集内容路由，返回所有文件类型 ---
@router.get("/{dataset_id}/browse_contents", tags=["Datasets"])
def browse_dataset_contents(
        dataset_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    获取数据集中所有文件和文件夹的列表，包括其相对路径和类型，以供前端浏览。
    """
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    # 权限检查：数据集所有者或公开数据集可浏览
    if dataset.owner_id != current_user.id and not dataset.is_public:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions")

    storage_path = Path(dataset.storage_path)
    base_uploads_dir = Path(settings.UPLOADS_DIR)

    # 安全检查：确保 storage_path 在允许的上传目录下
    if not storage_path.is_relative_to(base_uploads_dir):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid dataset path for security reasons.")

    relative_base_path_from_uploads = storage_path.relative_to(base_uploads_dir).as_posix()

    all_files_and_dirs = []

    # 递归遍历所有文件和目录
    for root, dirs, files in os.walk(storage_path):
        current_root_path = Path(root)
        # 计算当前目录相对于数据集根目录的路径
        relative_current_root = current_root_path.relative_to(storage_path).as_posix()
        if relative_current_root == '.':  # 根目录自身
            relative_current_root = ''

        # 添加目录
        for d in dirs:
            # 确保目录路径是安全的
            dir_relative_path = Path(relative_current_root) / d if relative_current_root else Path(d)
            if ".." in str(dir_relative_path) or str(dir_relative_path).startswith("/"):
                print(f"Warning: Skipping dangerous directory path: {dir_relative_path}")
                continue

            all_files_and_dirs.append({
                "name": d,
                "relative_path": dir_relative_path.as_posix(),
                "is_directory": True,
                "file_type": "folder"  # 自定义类型
            })

        # 添加文件
        for f in files:
            file_path = current_root_path / f
            # 确保文件路径是安全的
            file_relative_path = Path(relative_current_root) / f if relative_current_root else Path(f)
            if ".." in str(file_relative_path) or str(file_relative_path).startswith("/"):
                print(f"Warning: Skipping dangerous file path: {file_relative_path}")
                continue

            mime_type, _ = mimetypes.guess_type(str(file_path))  # 猜测MIME类型
            file_type = "other"
            if mime_type:
                if mime_type.startswith("image/"):
                    file_type = "image"
                elif mime_type.startswith("text/"):
                    file_type = "text"

            all_files_and_dirs.append({
                "name": f,
                "relative_path": file_relative_path.as_posix(),
                "is_directory": False,
                "file_type": file_type
            })

    # 排序：先目录后文件，然后按名称
    all_files_and_dirs.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))

    return {
        "base_url": f"/static_uploads/{relative_base_path_from_uploads}",
        "files": all_files_and_dirs  # 返回所有文件和目录的列表
    }


@router.get("/{dataset_id}/images", response_model=List[schemas.Image], tags=["Datasets"])
def read_images_in_dataset(
        dataset_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    获取指定数据集中的所有图片列表。
    需要验证用户对该数据集的访问权限。
    """
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    if dataset.owner_id != current_user.id and not dataset.is_public and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not enough permissions to access images in this dataset.")

    images = crud_image.get_images_by_dataset(db, dataset_id=dataset_id)
    return images


@router.post("/{dataset_id}/export_annotations", tags=["Datasets"])
def export_dataset_annotations(
        dataset_id: int,
        export_request: schemas.AnnotationExportRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> FileResponse:
    """
    导出指定数据集的标注数据为指定格式的ZIP包。
    """
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not enough permissions to export annotations for this dataset.")

    try:
        exported_zip_path = annotation_exporter.export_annotations(
            db=db,
            dataset_id=dataset_id,
            export_format=export_request.format,
            include_images=export_request.include_images  # <-- 使用前端传入的 include_images 参数
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Annotation export failed: {e}")

    if not exported_zip_path or not Path(exported_zip_path).exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create export archive.")

    background_tasks.add_task(os.remove, exported_zip_path)

    return FileResponse(
        path=exported_zip_path,
        media_type='application/zip',
        filename=f"{dataset.name.replace(' ', '_')}_{export_request.format.value}_annotations.zip"
    )


@router.post("/{dataset_id}/export-training-package", tags=["Datasets"])
def export_training_package(
        dataset_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> FileResponse:
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the dataset owner can export a training package.")
    stats = _annotation_stats(dataset)
    if stats["unreviewed_image_count"] > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"还有 {stats['unreviewed_image_count']} 张图片未检查标注。")
    manifest_path = _split_manifest_path(dataset)
    if not manifest_path.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先完成数据集自动划分。")
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    output_root = Path(settings.UPLOADS_DIR)
    try:
        archive_path = create_yolo_training_package(db, dataset, manifest, output_root)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    background_tasks.add_task(os.remove, archive_path)
    return FileResponse(path=archive_path, media_type="application/zip", filename=f"{dataset.name.replace(' ', '_')}_YOLO_training.zip")


@router.post("/{dataset_id}/export-experience-training-package", tags=["Datasets"])
def export_experience_training_package(
        dataset_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> FileResponse:
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能导出自己数据集的体验训练包。")
    annotated_images = [image for image in dataset.images or [] if image.annotations]
    if len(annotated_images) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "至少需要3张已经绘制缺陷标注的图片。")
    random.Random(42).shuffle(annotated_images)
    train_images = annotated_images[:-2]
    val_images = annotated_images[-2:-1]
    test_images = annotated_images[-1:]

    def items(images):
        return [{"id": image.id, "filename": image.filename, "relative_path": image.filename} for image in images]

    manifest = {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "mode": "experience_only",
        "warning": "少量标注样本，仅用于体验训练流程，不用于正式质检。",
        "seed": 42,
        "counts": {"total": len(annotated_images), "train": len(train_images), "val": 1, "test": 1},
        "splits": {"train": items(train_images), "val": items(val_images), "test": items(test_images)},
    }
    output_root = Path(settings.UPLOADS_DIR)
    try:
        archive_path = create_yolo_training_package(db, dataset, manifest, output_root, experience=True)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    background_tasks.add_task(os.remove, archive_path)
    filename = f"{dataset.name.replace(' ', '_')}_YOLO_experience_training.zip"
    return FileResponse(path=archive_path, media_type="application/zip", filename=filename)


@router.delete("/{dataset_id}", response_model=schemas.Dataset)
def delete_existing_dataset(
        dataset_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    删除一个数据集，包括其在服务器上的所有文件、关联的图片记录和标注。
    """
    dataset_to_delete = crud.crud_dataset.get_dataset(db, dataset_id)
    if not dataset_to_delete:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset_to_delete.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions to delete this dataset.")

    # 调用 CRUD 层删除数据集，CRUD 层会处理级联删除图片和标注
    deleted_dataset = crud.crud_dataset.delete_dataset(db, dataset_id=dataset_id)

    # 删除服务器上的实际存储文件夹
    storage_path = Path(deleted_dataset.storage_path)
    # 安全检查：确保路径在允许的上传目录下，防止误删系统文件
    base_uploads_dir = Path(settings.UPLOADS_DIR)
    if storage_path.is_relative_to(base_uploads_dir):
        try:
            shutil.rmtree(storage_path)
            print(f"Successfully deleted dataset folder: {storage_path}")
        except OSError as e:
            print(f"Warning: Could not delete dataset folder {storage_path}: {e}")
            # 这里不抛出HTTPException，因为数据库记录已删除，文件删除失败是次要问题
    else:
        print(
            f"Warning: Dataset storage path {storage_path} is outside expected uploads directory. Skipping file system deletion.")

    return deleted_dataset
