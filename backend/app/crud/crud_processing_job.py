from sqlalchemy.orm import Session
from typing import List

from ..db import models
from ..schemas import processing_job as job_schema


def create_job(db: Session, job_in: job_schema.ProcessingJobCreate, submitted_by_id: int,
               output_folder: str) -> models.ProcessingJob:
    """在数据库中创建新的处理任务记录"""
    # 将Pydantic模型列表转换为字典列表以存入JSON字段
    steps_dict = [step.dict() for step in job_in.processing_steps]

    db_job = models.ProcessingJob(
        source_dataset_id=job_in.source_dataset_id,
        output_folder_name=output_folder,
        processing_steps=steps_dict,
        submitted_by_id=submitted_by_id,
        status=models.JobStatus.pending
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_job(db: Session, job_id: int) -> models.ProcessingJob:
    """通过ID获取任务"""
    return db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()


def update_job_status(db: Session, job_id: int, status: models.JobStatus, progress: int = None):
    """更新任务的状态和进度"""
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        if progress is not None:
            db_job.progress = progress
        db.commit()
        db.refresh(db_job)
    return db_job