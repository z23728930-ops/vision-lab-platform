# defect-detection-backend/app/api/routers/inference.py

import shutil
import os # <-- 新增导入 os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse # <-- 新增导入 FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import time
import cv2
import csv
import io
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from ... import crud, schemas
from ...core.config import settings
from ...db import models
from ...db.base import get_db
from ..deps import get_current_active_user, get_current_admin_user
from ...services.inference_runner import run_inference_job
from ...services.model_runner import get_model_runner

router = APIRouter()

@router.post("/jobs", response_model=schemas.InferenceJob, status_code=status.HTTP_202_ACCEPTED)
def create_new_inference_job(
        *,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        job_in: schemas.InferenceJobCreate,
        background_tasks: BackgroundTasks
):
    source_dataset = crud.crud_dataset.get_dataset(db, job_in.source_dataset_id) # 使用 crud.crud_dataset
    model = crud.crud_model.get_model(db, job_in.model_id) # 假设您有 crud.crud_model

    if not source_dataset or not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset or Model not found.")

    output_path = Path(
        settings.UPLOADS_DIR) / "inference_results" / f"{job_in.job_name.replace(' ', '_')}_{int(time.time())}"

    new_job = crud.crud_inference.create_inference_job(db, job_in=job_in, user_id=current_user.id, output_path=str(output_path)) # 使用 crud.crud_inference

    background_tasks.add_task(
        run_inference_job,
        job_id=new_job.id,
        source_dataset_path=source_dataset.storage_path,
        model_path=model.file_path,
        model_type=model.model_type,
        output_path=str(output_path),
        params=job_in.inference_params
    )
    return new_job


@router.get("/jobs", response_model=list[schemas.InferenceJob])
def read_inference_jobs(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """获取当前用户的所有推理任务"""
    return crud.crud_inference.get_inference_jobs_by_user(db, user_id=current_user.id) # 使用 crud.crud_inference


@router.get("/admin/jobs", response_model=list[schemas.InferenceJob])
def read_all_inference_jobs_for_admin(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    """管理员查看全部学生推理任务，供实验课过程监控使用。"""
    return db.query(models.InferenceResult).order_by(models.InferenceResult.created_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=schemas.InferenceJob)
def get_inference_job(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id)  # 使用 crud.crud_inference
    if not job: raise HTTPException(404, "Job not found")
    if job.created_by_id != current_user.id: raise HTTPException(403, "Not enough permissions")
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inference_job(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id) # 使用 crud.crud_inference
    if not job: raise HTTPException(404, "Job not found")
    if job.created_by_id != current_user.id: raise HTTPException(403, "Not enough permissions")

    crud.crud_inference.delete_inference_job(db, job_id=job_id) # 使用 crud.crud_inference
    # 204 No Content 响应不需要返回 body


@router.get("/jobs/{job_id}/browse")
def browse_inference_result(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id) # 使用 crud.crud_inference
    if not job: raise HTTPException(404, "Job not found")
    if job.created_by_id != current_user.id: raise HTTPException(403, "Not enough permissions")
    if job.status != models.JobStatus.completed: # 只能浏览已完成的任务
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Inference job is not completed yet.")

    storage_path = Path(job.output_path)
    # 确保存储路径在允许的上传目录下，增加安全性
    if not storage_path.is_relative_to(settings.UPLOADS_DIR):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage path.")

    base_uploads_dir = Path(settings.UPLOADS_DIR)

    # 计算相对于静态文件服务根目录的路径
    # 假设静态文件通过 /static_uploads 挂载在 settings.UPLOADS_DIR
    relative_path_from_uploads = storage_path.relative_to(base_uploads_dir)

    # 列出所有图片文件（例如 .png, .jpg, .jpeg）
    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        # 使用 rglob 递归查找所有子目录中的图片
        image_files.extend([p.relative_to(storage_path).as_posix() for p in storage_path.rglob(ext)]) # 返回相对路径
    image_files.sort()  # 排序以保持一致性

    return {
        "base_url": f"/static_uploads/{relative_path_from_uploads.as_posix()}",
        "images": image_files
    }

@router.get("/jobs/{job_id}/stats")
def inference_result_stats(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id)
    if not job or job.created_by_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inference job not found")
    summary = job.results_summary if isinstance(job.results_summary, dict) else {}
    path = Path(job.output_path) if job.output_path else None
    result_images = []
    if path and path.exists():
        result_images = [p for p in path.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}]
    return {"job_id": job.id, "status": job.status.value, "result_image_count": len(result_images), "progress": summary.get("progress", 0), "images_processed": summary.get("images_processed", 0), "error": summary.get("error")}

@router.get("/jobs/{job_id}/report.csv")
def download_inference_report(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id)
    if not job or job.created_by_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inference job not found")
    summary = job.results_summary if isinstance(job.results_summary, dict) else {}
    path = Path(job.output_path) if job.output_path else None
    result_files = sorted([p for p in path.rglob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg','.bmp','.tiff'}]) if path and path.exists() else []
    result_count = len(result_files)
    stream = io.StringIO(); stream.write('\ufeff')
    writer = csv.writer(stream); writer.writerow(['任务汇总']); writer.writerow(['任务编号','任务名称','状态','进度','已处理图片','结果图片','失败原因'])
    writer.writerow([job.id, job.job_name, job.status.value, summary.get('progress', 0), summary.get('images_processed', 0), result_count, summary.get('error', '')])
    writer.writerow([]); writer.writerow(['结果文件明细']); writer.writerow(['序号','原图文件名（推测）','结果文件名','相对路径'])
    for index, result_file in enumerate(result_files, 1):
        result_name = result_file.name
        original_name = result_name[:-9] if result_name.lower().endswith('_mask.png') else result_name
        writer.writerow([index, original_name, result_name, result_file.relative_to(path).as_posix()])
    return StreamingResponse(iter([stream.getvalue()]), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename=inference_{job.id}_report.csv'})

@router.get("/jobs/{job_id}/report.json")
def inference_report_json(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    job = crud.crud_inference.get_inference_job(db, job_id=job_id)
    if not job or job.created_by_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inference job not found")
    summary = job.results_summary if isinstance(job.results_summary, dict) else {}
    path = Path(job.output_path) if job.output_path else None
    files = sorted([p for p in path.rglob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg','.bmp','.tiff'}]) if path and path.exists() else []
    return JSONResponse({"job_id": job.id, "job_name": job.job_name, "status": job.status.value, "summary": summary, "result_files": [{"name": p.name, "relative_path": p.relative_to(path).as_posix()} for p in files]})

# --- 新增：下载推理结果的 API 端点 ---
@router.get("/jobs/{job_id}/download")
def download_inference_result(
        job_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    下载指定推理任务的结果 (压缩为zip)。
    """
    job = crud.crud_inference.get_inference_job(db, job_id=job_id) # 使用 crud.crud_inference
    if not job:
        raise HTTPException(status_code=404, detail="Inference job not found")
    if job.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to download this result.")
    if job.status != models.JobStatus.completed:
        raise HTTPException(status_code=400, detail="Inference job is not completed yet.")

    path_to_archive = Path(job.output_path)
    if not path_to_archive.exists() or not path_to_archive.is_dir():
        raise HTTPException(status_code=404, detail="Results directory not found on server.")

    # 确保存储路径在允许的上传目录下，增加安全性
    if not path_to_archive.is_relative_to(settings.UPLOADS_DIR):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage path for download.")

    # 创建临时的zip文件
    # base_name 应该包含完整路径和文件名，不含扩展名
    temp_zip_name_base = Path(
        settings.UPLOADS_DIR) / f"temp_inference_download_{job.job_name.replace(' ', '_')}_{int(time.time())}"

    # shutil.make_archive 会创建 zip 文件并返回其完整路径
    temp_zip_name = shutil.make_archive(
        base_name=str(temp_zip_name_base),  # make_archive 需要字符串路径
        format='zip',
        root_dir=str(path_to_archive)  # root_dir 是要压缩的目录
    )

    # 将删除临时文件的任务添加到后台
    background_tasks.add_task(os.remove, temp_zip_name)

    return FileResponse(
        path=temp_zip_name,
        media_type='application/zip',
        filename=f"{job.job_name.replace(' ', '_')}_results.zip"
    )

@router.post("/single", dependencies=[Depends(get_current_active_user)])
async def inference_single_image(
        model_id: int = Form(...),
        image: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    model = crud.crud_model.get_model(db, model_id) # 使用 crud.crud_model
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found.")

    timestamp = int(time.time() * 1000)
    output_dir = Path(settings.UPLOADS_DIR) / "single_inference" / str(timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)

    original_image_path = output_dir / image.filename
    with open(original_image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    model_runner = get_model_runner(model.model_type, model.file_path, {})
    cv_image = cv2.imread(str(original_image_path))

    # 检查图片是否成功加载
    if cv_image is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not read image file.")

    # 如果模型返回的不是OpenCV格式，需要转换
    result_mask = model_runner.run(cv_image)

    mask_filename = f"{original_image_path.stem}_mask.png"
    mask_path = output_dir / mask_filename
    cv2.imwrite(str(mask_path), result_mask)

    base_url = "/static_uploads"
    # 从 settings.UPLOADS_DIR 到 output_dir 的相对路径
    relative_output_dir = output_dir.relative_to(Path(settings.UPLOADS_DIR))

    original_url = f"{base_url}/{relative_output_dir.as_posix()}/{image.filename}"
    mask_url = f"{base_url}/{relative_output_dir.as_posix()}/{mask_filename}"

    return {"original_image_url": original_url, "mask_image_url": mask_url}
