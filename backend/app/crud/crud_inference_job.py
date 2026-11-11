# defect-detection-backend/app/crud/crud_inference.py

from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import models
from app.schemas import InferenceJobCreate
from pathlib import Path
import shutil
from sqlalchemy.orm.attributes import flag_modified # <-- 新增导入

class CRUDInference:
    def create_inference_job(
            self,
            db: Session,
            job_in: InferenceJobCreate,
            user_id: int,
            output_path: str
    ) -> models.InferenceResult:
        db_job = models.InferenceResult(
            job_name=job_in.job_name,
            source_dataset_id=job_in.source_dataset_id,
            model_id=job_in.model_id,
            inference_params=job_in.inference_params,
            output_path=output_path,
            created_by_id=user_id,
            status=models.JobStatus.pending,  # 初始状态为 pending
            results_summary={"progress": 0}  # 初始化进度
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job


    def get_inference_job(self, db: Session, job_id: int) -> Optional[models.InferenceResult]:
        return db.query(models.InferenceResult).filter(models.InferenceResult.id == job_id).first()


    def get_inference_jobs_by_user(self, db: Session, user_id: int) -> List[models.InferenceResult]:
        return db.query(models.InferenceResult).filter(models.InferenceResult.created_by_id == user_id).all()


    def update_inference_job_status(
            self,
            db: Session,
            job_id: int,
            status: models.JobStatus,
            summary: Optional[dict] = None  # 可以更新进度或其他总结信息
    ) -> Optional[models.InferenceResult]:
        db_job = self.get_inference_job(db, job_id=job_id)
        if db_job:
            db_job.status = status
            if summary is not None:
                # 确保 results_summary 是一个字典，如果不是则初始化为字典
                if not isinstance(db_job.results_summary, dict):
                    db_job.results_summary = {}
                db_job.results_summary.update(summary)
                # --- 关键修复：显式标记 JSON 字段已修改 ---
                flag_modified(db_job, "results_summary")
                # ----------------------------------------
            db.commit()
            db.refresh(db_job)
        return db_job


    def delete_inference_job(self, db: Session, job_id: int):
        db_job = self.get_inference_job(db, job_id=job_id)
        if db_job:
            if db_job.output_path and Path(db_job.output_path).exists():
                try:
                    shutil.rmtree(db_job.output_path)
                    print(f"Deleted inference results directory: {db_job.output_path}")
                except Exception as e:
                    print(f"Error deleting inference results directory {db_job.output_path}: {e}")

            db.delete(db_job)
            db.commit()

# 实例化 CRUDInference 类，以便在其他模块中导入和使用
crud_inference = CRUDInference()