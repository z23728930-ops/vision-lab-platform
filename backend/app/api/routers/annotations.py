# app/api/routers/annotations.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List

from ... import crud, schemas
from ...db import models
from ...db.base import get_db
from ..deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=schemas.Annotation, status_code=status.HTTP_201_CREATED, tags=["Annotations"])
def create_annotation(
        annotation_in: schemas.AnnotationCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    创建一个新的标注。
    需要验证用户对目标数据集的写权限 (即为数据集所有者)。
    """
    dataset = crud.crud_dataset.get_dataset(db, dataset_id=annotation_in.dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to annotate this dataset.")

    # 验证 image_id 是否属于该 dataset_id
    image = crud.crud_image.get_image(db, image_id=annotation_in.image_id)
    if not image or image.dataset_id != annotation_in.dataset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image does not belong to the specified dataset.")

    new_annotation = crud.crud_annotation.create_annotation(db, annotation_in=annotation_in)
    return new_annotation


@router.post("/batch", response_model=List[schemas.Annotation], status_code=status.HTTP_201_CREATED, tags=["Annotations"])
def create_batch_annotations(
        batch_in: schemas.AnnotationBatchCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    批量创建标注。
    所有标注必须属于同一个数据集，并验证用户对该数据集的写权限。
    """
    if not batch_in.annotations:
        return []

    # 验证所有标注是否属于同一个数据集，并获取数据集ID
    dataset_id = batch_in.annotations[0].dataset_id
    for ann in batch_in.annotations:
        if ann.dataset_id != dataset_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All annotations in a batch must belong to the same dataset.")

    dataset = crud.crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to annotate this dataset.")

    # 验证所有 image_id 是否有效且属于该数据集
    image_ids = {ann.image_id for ann in batch_in.annotations}
    db_images = crud.crud_image.get_images_by_dataset(db, dataset_id=dataset_id)
    valid_image_ids_in_dataset = {img.id for img in db_images}
    if not image_ids.issubset(valid_image_ids_in_dataset):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more image IDs in the batch are invalid or do not belong to the specified dataset.")


    new_annotations = crud.crud_annotation.create_multiple_annotations(db, annotations_in=batch_in.annotations)
    return new_annotations


@router.get("/images/{image_id}/annotations", response_model=List[schemas.Annotation], tags=["Annotations"])
def read_annotations_by_image(
        image_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    获取指定图片的所有标注。
    需要验证用户对图片所属数据集的读权限。
    """
    image = crud.crud_image.get_image(db, image_id=image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")

    dataset = crud.crud_dataset.get_dataset(db, dataset_id=image.dataset_id)
    if not dataset: # 理论上不会发生，除非数据不一致
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated dataset not found.")

    # 权限检查：数据集所有者、公开数据集或管理员可读
    if dataset.owner_id != current_user.id and not dataset.is_public and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to view annotations for this image.")

    annotations = crud.crud_annotation.get_annotations_by_image(db, image_id=image_id)
    return annotations


@router.put("/{annotation_id}", response_model=schemas.Annotation, tags=["Annotations"])
def update_annotation(
        annotation_id: int,
        annotation_update: schemas.AnnotationUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    更新单个标注。
    需要验证用户对标注所属数据集的写权限。
    """
    db_annotation = crud.crud_annotation.get_annotation(db, annotation_id=annotation_id)
    if not db_annotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")

    dataset = crud.crud_dataset.get_dataset(db, dataset_id=db_annotation.dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this annotation.")

    updated_annotation = crud.crud_annotation.update_annotation(db, annotation_id=annotation_id, annotation_update=annotation_update)
    if not updated_annotation: # 理论上不会发生，因为前面已检查
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update annotation.")
    return updated_annotation


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Annotations"])
def delete_annotation(
        annotation_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> None:
    """
    删除单个标注。
    需要验证用户对标注所属数据集的写权限。
    """
    db_annotation = crud.crud_annotation.get_annotation(db, annotation_id=annotation_id)
    if not db_annotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")

    dataset = crud.crud_dataset.get_dataset(db, dataset_id=db_annotation.dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated dataset not found.")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this annotation.")

    crud.crud_annotation.delete_annotation(db, annotation_id=annotation_id)
    return


@router.post("/delete-batch", status_code=status.HTTP_204_NO_CONTENT, tags=["Annotations"])
def delete_batch_annotations(
        annotation_ids: List[int], # 直接接收ID列表
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> None:
    """
    批量删除标注。
    需要验证用户对所有标注所属数据集的写权限。
    """
    if not annotation_ids:
        return

    # 获取所有待删除标注，并验证权限
    annotations_to_delete = db.query(models.Annotation).filter(models.Annotation.id.in_(annotation_ids)).all()
    if len(annotations_to_delete) != len(annotation_ids):
        # 存在部分ID未找到，或者ID重复
        found_ids = {ann.id for ann in annotations_to_delete}
        missing_ids = set(annotation_ids) - found_ids
        if missing_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Some annotations not found: {list(missing_ids)}")

    # 检查所有标注是否属于当前用户有权限的数据集
    for ann in annotations_to_delete:
        dataset = crud.crud_dataset.get_dataset(db, dataset_id=ann.dataset_id)
        if not dataset or (dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not enough permissions to delete annotation ID {ann.id}.")

    crud.crud_annotation.delete_multiple_annotations(db, annotation_ids)
    return
