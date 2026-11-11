from pathlib import Path
import cv2
import glob
import numpy as np
from .model_runner import get_model_runner
from ..db.base import SessionLocal
from ..crud.crud_inference_job import crud_inference
from ..services.notification_service import notification_service
from .. import crud
from ..db import models
import time


def run_inference_job(job_id: int, source_dataset_path: str, model_path: str, model_type: str, output_path: str,
                      params: dict):
    db = SessionLocal()
    job_status = models.JobStatus.pending
    try:
        started_at = time.time()
        # 获取当前任务对象，确保每次更新都基于最新数据
        db_job = crud_inference.get_inference_job(db, job_id)
        if not db_job:
            print(f"[ERROR] Inference job {job_id} not found in DB.")
            raise ValueError(f"Inference job {job_id} not found.")

        # 初始化或更新任务状态为 running
        crud_inference.update_inference_job_status(db, job_id, status=models.JobStatus.running, summary={"progress": 0,
                                                                                                         "images_processed": 0})  # 确保初始化时就有 images_processed
        job_status = models.JobStatus.running  # 更新局部状态变量

        # 1. 加载模型
        model_runner = get_model_runner(model_type, model_path, params)

        # 2. 查找图片
        source_dir = Path(source_dataset_path)
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        image_paths = []
        supported_formats = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        for fmt in supported_formats:
            image_paths.extend(source_dir.rglob(fmt))

        if not image_paths:
            raise ValueError("No images found in the source dataset.")

        total_images = len(image_paths)  # 获取总图片数

        # 3. 循环推理
        for i, img_path in enumerate(image_paths):
            image = None
            try:
                with open(img_path, 'rb') as f:
                    bytes_data = f.read()
                    image = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                print(
                    f"[INFERENCE JOB {job_id}] WARNING: Could not read or decode image {img_path.name}: {e}. Skipping.")
                continue

            if image is None:
                print(f"[INFERENCE JOB {job_id}] WARNING: Image {img_path.name} is empty after decoding. Skipping.")
                continue

            result_mask = model_runner.run(image)

            output_mask_path = output_dir / f"{img_path.stem}_mask.png"
            is_success, buffer = cv2.imencode('.png', result_mask)
            if is_success:
                try:
                    with open(output_mask_path, 'wb') as f:
                        f.write(buffer.tobytes())
                except Exception as e:
                    print(
                        f"[INFERENCE JOB {job_id}] WARNING: Could not save processed image to {output_mask_path}: {e}. Skipping.")
            else:
                print(
                    f"[INFERENCE JOB {job_id}] WARNING: Could not encode result mask for {img_path.name}. Skipping save.")

            progress = int(((i + 1) / total_images) * 100)
            current_summary = {
                "progress": progress,
                "images_processed": i + 1  # 正在运行时显示已处理数量
            }
            crud_inference.update_inference_job_status(db, job_id, status=models.JobStatus.running,
                                                       summary=current_summary)

        # 4. 任务完成，最终更新状态和 summary
        final_summary = {
            "images_processed": total_images,  # 确保这里是总图片数
            "progress": 100
        }
        crud_inference.update_inference_job_status(db, job_id, status=models.JobStatus.completed, summary=final_summary)
        job_status = models.JobStatus.completed

    except Exception as e:
        import traceback
        traceback.print_exc()
        crud_inference.update_inference_job_status(db, job_id, status=models.JobStatus.failed,
                                                   summary={"error": str(e), "progress": 0,
                                                            "images_processed": 0})  # 失败时也包含 images_processed
        job_status = models.JobStatus.failed
    finally:
        # 再次获取最新任务对象，确保邮件发送时数据最新
        # 这一步非常重要，确保从数据库中加载的是最新的、已通过 flag_modified 持久化的数据
        job = crud_inference.get_inference_job(db, job_id)
        if job and job.created_by_id:
            user = crud.get_user(db, user_id=job.created_by_id)

            # --- 最终调试打印，确认邮件发送前的数据 ---
            print(f"[DEBUG_EMAIL_FINAL] Job ID: {job.id}")
            print(f"[DEBUG_EMAIL_FINAL] Job Status: {job_status.value}")
            print(f"[DEBUG_EMAIL_FINAL] Job results_summary: {job.results_summary}")
            print(f"[DEBUG_EMAIL_FINAL] Type of results_summary: {type(job.results_summary)}")
            # ----------------------------------------

            if user and user.email and user.receive_notifications:
                subject = f"推理任务 '{job.job_name}' 已{job_status.value}"
                body = f"您的推理任务 '{job.job_name}' (ID: {job.id}) 已{job_status.value}。\n"

                processed_images_count = 0
                error_message = '未知错误'

                if isinstance(job.results_summary, dict):
                    if job_status == models.JobStatus.completed:
                        processed_images_count = job.results_summary.get('images_processed', 0)
                        body += f"共处理图片: {processed_images_count} 张。\n"
                    elif job_status == models.JobStatus.failed:
                        error_message = job.results_summary.get('error', '未知错误')
                        body += f"错误信息: {error_message}\n"
                else:
                    print(f"[WARNING] results_summary for job {job.id} is not a dictionary: {job.results_summary}")
                    if job_status == models.JobStatus.completed:
                        body += f"共处理图片: 0 张 (数据异常)。\n"
                    elif job_status == models.JobStatus.failed:
                        body += f"错误信息: 未知错误 (数据异常)。\n"

                body += "\n请登录系统查看详情。"
                notification_service.send_email(user.email, subject, body)
        db.close()
