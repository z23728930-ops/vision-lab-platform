from pathlib import Path
import cv2
import glob
import numpy as np
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from ..db.base import SessionLocal
from .. import crud
from ..db import models


def apply_processing(image, steps: List[Dict[str, Any]]):
    """对单个图像应用一系列处理步骤"""
    img = image

    # 辅助函数：确保图像是灰度图，如果不是则转换
    def ensure_grayscale(img_to_check):
        if len(img_to_check.shape) == 3 and img_to_check.shape[2] == 3:
            return cv2.cvtColor(img_to_check, cv2.COLOR_BGR2GRAY)
        return img_to_check

    for step in steps:
        op_type = step.get("type")
        params = step.get("params", {})

        if op_type == "grayscale":
            # 确保图像是3通道的才能转灰度
            if len(img.shape) == 3 and img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        elif op_type == "gaussian_blur":
            ksize = params.get("kernel_size", 5)
            # 核大小必须是正奇数
            if ksize > 0 and ksize % 2 == 1:
                img = cv2.GaussianBlur(img, (ksize, ksize), 0)
            else:
                print(f"Warning: gaussian_blur kernel_size {ksize} is not a positive odd number. Skipping.")
        elif op_type == "median_blur":
            ksize = params.get("kernel_size", 5)
            if ksize > 0 and ksize % 2 == 1:
                img = cv2.medianBlur(img, ksize)
            else:
                print(f"Warning: median_blur kernel_size {ksize} is not a positive odd number. Skipping.")

        # --- 新增的图像处理功能 ---
        elif op_type == "flip":
            # code: 0 (垂直翻转), 1 (水平翻转), -1 (水平垂直都翻转)
            flip_code = params.get("code")
            if flip_code in [0, 1, -1]:
                img = cv2.flip(img, flip_code)
            else:
                print(f"Warning: flip code {flip_code} is invalid. Must be 0, 1, or -1. Skipping.")

        elif op_type == "resize":
            width = params.get("width")
            height = params.get("height")
            scale_factor = params.get("scale_factor")

            if width and height and width > 0 and height > 0:
                if width < 32 or height < 32:
                    raise ValueError("调整后的宽度和高度不能小于 32 像素；qk 模型建议使用 512×512")
                img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
            elif scale_factor and scale_factor > 0:
                img = cv2.resize(img, (0, 0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
            else:
                print(
                    "Warning: resize operation requires valid 'width' and 'height' or a positive 'scale_factor'. Skipping.")

        elif op_type == "rotate":
            # angle: 90, 180, 270 (顺时针)
            angle = params.get("angle")
            if angle == 90:
                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                img = cv2.rotate(img, cv2.ROTATE_180)
            elif angle == 270:
                img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                print(f"Warning: rotate angle {angle} is not supported (only 90, 180, 270). Skipping.")

        elif op_type == "brightness_contrast":
            alpha = params.get("alpha", 1.0)  # 对比度控制 (1.0-3.0 常用范围)
            beta = params.get("beta", 0)  # 亮度控制 (0-100 常用范围)
            # convertScaleAbs 将像素值缩放到 [0, 255] 范围并转换为 8-bit 无符号整数
            img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        elif op_type == "invert_colors":
            # 对图像的每个像素执行位反转操作
            img = cv2.bitwise_not(img)

        elif op_type == "sharpen":
            # 定义一个简单的锐化核（拉普拉斯核的变体）
            kernel = np.array([
                [0, -1, 0],
                [-1, 5, -1],
                [0, -1, 0]
            ])
            # -1 表示输出图像与输入图像具有相同的深度（数据类型）
            img = cv2.filter2D(img, -1, kernel)

        elif op_type == "canny_edge":
            img = ensure_grayscale(img)  # Canny 边缘检测通常在灰度图上效果最好
            threshold1 = params.get("threshold1", 100)
            threshold2 = params.get("threshold2", 200)
            img = cv2.Canny(img, threshold1, threshold2)

        elif op_type == "threshold":
            img = ensure_grayscale(img)  # 阈值化操作需要灰度图
            thresh = params.get("thresh", 127)  # 阈值
            maxval = params.get("maxval", 255)  # 超过阈值时设置的最大值
            thresh_type_str = params.get("type", "binary")  # 阈值类型

            thresh_type_map = {
                "binary": cv2.THRESH_BINARY,
                "binary_inv": cv2.THRESH_BINARY_INV,
                "trunc": cv2.THRESH_TRUNC,
                "tozero": cv2.THRESH_TOZERO,
                "tozero_inv": cv2.THRESH_TOZERO_INV,
                "otsu": cv2.THRESH_OTSU  # Otsu 方法会自动计算最佳阈值，此时 `thresh` 参数会被忽略
            }

            thresh_type = thresh_type_map.get(thresh_type_str)
            if thresh_type is not None:
                if thresh_type_str == "otsu":
                    # Otsu 阈值化通常与 THRESH_BINARY 结合使用
                    _, img = cv2.threshold(img, 0, maxval, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                else:
                    _, img = cv2.threshold(img, thresh, maxval, thresh_type)
            else:
                print(f"Warning: Unknown threshold type '{thresh_type_str}'. Skipping.")

        else:
            print(f"Warning: Unknown processing type '{op_type}'. Skipping this step.")

    return img


def run_processing_job(
        job_id: int,
        source_path: str,
        dest_path: str,
        steps: List[Dict[str, Any]],
        output_name: str,
        owner_id: int,
        source_dataset_id: int,
):
    """后台任务执行的函数"""
    print(f"\n[JOB {job_id}] Starting background processing job.")
    db: Session = SessionLocal()
    try:
        print(f"[JOB {job_id}] Updating job status to 'running'.")
        crud.update_job_status(db, job_id=job_id, status=models.JobStatus.running, progress=0)

        source_dir = Path(source_path)
        dest_dir = Path(dest_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"[JOB {job_id}] Source directory: {source_dir}")
        print(f"[JOB {job_id}] Destination directory: {dest_dir}")

        image_paths = []
        supported_formats = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']

        print(f"[JOB {job_id}] Recursively searching for images in source directory...")
        for fmt in supported_formats:
            found_files = list(source_dir.rglob(fmt))  # 使用 rglob 递归搜索
            if found_files:
                print(f"[JOB {job_id}] Found {len(found_files)} files with format {fmt}.")
                image_paths.extend(found_files)

        if not image_paths:
            print(f"[JOB {job_id}] No supported image files found in the source directory. Marking job as failed.")
            crud.update_job_status(db, job_id=job_id, status=models.JobStatus.failed, progress=0)  # 明确设置为0
            return

        total_images = len(image_paths)
        print(f"[JOB {job_id}] Found a total of {total_images} images to process.")

        processed_count = 0
        for i, img_path in enumerate(image_paths):
            image = None  # 初始化
            try:
                # 获取相对于源目录的路径，以便在目标目录中保持相同的结构
                relative_path = img_path.relative_to(source_dir)
                output_image_path = dest_dir / relative_path

                # 确保目标文件的父目录存在
                output_image_path.parent.mkdir(parents=True, exist_ok=True)

                print(f"[JOB {job_id}] Processing image {i + 1}/{total_images}: {relative_path}")

                # --- 关键修改：使用 cv2.imdecode 来处理包含非 ASCII 字符的路径 ---
                with open(img_path, 'rb') as f:
                    bytes_data = np.frombuffer(f.read(), np.uint8)
                    image = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)

                if image is None:
                    print(f"[JOB {job_id}] WARNING: Could not decode image {img_path.name}. Skipping.")
                    continue  # 跳过无法解码的图片

                processed_image = apply_processing(image, steps)

                # --- 关键修改：使用 cv2.imencode 和文件写入来处理保存时的非 ASCII 路径 ---
                # 确定图片格式（例如，从原文件名后缀获取）
                file_extension = img_path.suffix.lower()
                if file_extension == '.jpg' or file_extension == '.jpeg':
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]  # JPEG质量
                elif file_extension == '.png':
                    encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 9]  # PNG压缩等级
                else:
                    encode_param = []  # 其他格式使用默认参数

                is_success, buffer = cv2.imencode(file_extension, processed_image, encode_param)
                if is_success:
                    with open(output_image_path, 'wb') as f:
                        f.write(buffer)
                    processed_count += 1
                else:
                    print(
                        f"[JOB {job_id}] WARNING: Could not encode/save processed image to {output_image_path}. Skipping.")
                    continue  # 跳过无法保存的图片

            except Exception as img_process_e:
                print(f"[JOB {job_id}] Error processing image {img_path}: {img_process_e}. Skipping this image.")
                continue  # 跳过当前图片，继续处理下一张

            # 4. 更新进度
            progress = int(((i + 1) / total_images) * 100)
            # 每处理5%的图片或最后一张图片时更新一次数据库，避免频繁IO
            if progress % 5 == 0 or (i + 1) == total_images:
                print(f"[JOB {job_id}] Progress: {progress}%")
                crud.update_job_status(db, job_id=job_id, status=models.JobStatus.running, progress=progress)

        if processed_count == 0:
            raise RuntimeError("没有图片成功完成预处理，请检查源图片格式和文件内容")

        from ..crud.crud_dataset import crud_dataset
        from ..schemas.dataset import DatasetCreate
        new_dataset = crud_dataset.create_dataset(
            db,
            dataset=DatasetCreate(
                name=output_name,
                description=f"Processed from dataset ID {source_dataset_id}"
            ),
            owner_id=owner_id,
            storage_path=str(dest_path),
        )

        from ..crud.crud_image import crud_image
        from ..schemas.image import ImageCreate
        output_root = Path(dest_path)
        image_records = [
            ImageCreate(
                dataset_id=new_dataset.id,
                file_path=str(image_path),
                filename=image_path.name,
            )
            for image_path in output_root.rglob("*")
            if image_path.is_file() and image_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}
        ]
        if not image_records:
            raise RuntimeError("预处理文件已生成，但没有找到可登记的图片")
        crud_image.create_multiple_images(db, image_records)

        print(f"[JOB {job_id}] Processing finished ({processed_count}/{total_images}). Updating status to 'completed'.")
        crud.update_job_status(db, job_id=job_id, status=models.JobStatus.completed, progress=100)

    except Exception as e:
        print(f"[JOB {job_id}] An unexpected error occurred: {e}")  # 记录日志
        import traceback
        traceback.print_exc()  # 打印完整的堆栈信息，方便调试
        crud.update_job_status(db, job_id=job_id, status=models.JobStatus.failed, progress=0)  # 明确设置为0
    finally:
        print(f"[JOB {job_id}] Closing database session.")
        db.close()
