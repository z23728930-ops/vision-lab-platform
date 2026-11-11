from sqlalchemy.orm import Session
from pathlib import Path
import shutil
from ..db import models
from ..schemas import model as model_schema

def get_model(db: Session, model_id: int):
    return db.query(models.Model).filter(models.Model.id == model_id, models.Model.is_deleted == False).first()

def get_models(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Model).filter(models.Model.is_deleted == False).offset(skip).limit(limit).all()

def create_model(db: Session, model: model_schema.ModelCreate, file_path: str, user_id: int):
    db_model = models.Model(**model.model_dump(), file_path=file_path, uploaded_by_id=user_id)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def delete_model(db: Session, model_id: int):
    db_model = get_model(db, model_id)
    if db_model:
        # 软删除
        db_model.is_deleted = True
        db.commit()
        # 如果需要硬删除，取消下面注释并删除文件
        # Path(db_model.file_path).unlink(missing_ok=True)
        # db.delete(db_model)
        # db.commit()
    return db_model