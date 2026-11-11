import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ... import schemas
from ...crud.crud_dataset import crud_dataset # <-- 修改：导入 crud_dataset 实例
from ... import crud # <-- 保留此行，用于 crud.create_job 和 crud.get_job
from ...core.config import settings
from ...db import models
from ...db.base import get_db
from ..deps import get_current_active_user
from ...services.image_processor import apply_processing, run_processing_job

router = APIRouter()


@router.post("/preview")
async def preview_processing_image(
        image: UploadFile = File(...),
        steps: str = Form(...),
        current_user: models.User = Depends(get_current_active_user),
) -> Response:
    """Apply preprocessing steps to one image without creating a dataset."""
    try:
        parsed_steps = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="处理步骤格式无效") from exc
    if not isinstance(parsed_steps, list) or not parsed_steps:
        raise HTTPException(status_code=400, detail="请至少添加一个处理步骤")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传的图片为空")
    source = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if source is None:
        raise HTTPException(status_code=400, detail="无法读取该图片，请使用 JPG、PNG 或 BMP 图片")

    try:
        processed = apply_processing(source, parsed_steps)
        success, buffer = cv2.imencode(".png", processed)
        if not success:
            raise ValueError("image encoding failed")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"生成预览失败：{exc}") from exc

    return Response(content=buffer.tobytes(), media_type="image/png")


@router.post("/jobs", response_model=schemas.ProcessingJob, status_code=status.HTTP_202_ACCEPTED)
def create_new_processing_job(
        *,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        job_in: schemas.ProcessingJobCreate,
        background_tasks: BackgroundTasks,
) -> Any:
    """
    创建并启动一个新的图像预处理任务。
    这是一个异步操作，会立即返回任务信息。
    """
    # 1. 检查源数据集是否存在且属于当前用户
    source_dataset = crud_dataset.get_dataset(db, dataset_id=job_in.source_dataset_id) # <-- 修改：使用 crud_dataset 实例
    if not source_dataset:
        raise HTTPException(status_code=404, detail="Source dataset not found")
    if source_dataset.owner_id != current_user.id and not source_dataset.is_public:
        raise HTTPException(status_code=403, detail="只能预处理自己的数据集或公共数据集")

    # 2. 创建输出目录路径
    output_folder_name = f"{job_in.output_name.replace(' ', '_')}_{int(time.time())}"
    output_path = Path(settings.UPLOADS_DIR) / "datasets" / str(current_user.id) / output_folder_name

    # 3. 在数据库中创建任务记录
    new_job = crud.create_job(db, job_in=job_in, submitted_by_id=current_user.id, output_folder=str(output_path))

    # 4. 将实际的处理函数添加到后台任务
    background_tasks.add_task(
        run_processing_job,
        job_id=new_job.id,
        source_path=source_dataset.storage_path,
        dest_path=str(output_path),
        steps=[step.model_dump() for step in job_in.processing_steps],
        output_name=job_in.output_name,
        owner_id=current_user.id,
        source_dataset_id=source_dataset.id,
    )

    # 5. 同时，在datasets表中也创建一个新记录，方便管理
    return new_job


@router.get("/jobs/{job_id}", response_model=schemas.ProcessingJob)
def get_job_status(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    获取特定处理任务的状态和进度。
    """
    job = crud.get_job(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.submitted_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return job
