# defect-detection-backend/app/crud/crud_dataset.py

from pathlib import Path
from sqlalchemy.orm import Session, joinedload # <-- 新增导入 joinedload
from typing import List, Optional
from sqlalchemy import or_

from app.db import models
import shutil
from app.schemas import dataset as dataset_schema
from app.db.models import UserRole

class CRUDDataset:
    def get_dataset(self, db: Session, dataset_id: int) -> Optional[models.Dataset]:
        """通过ID获取单个数据集，并加载所有者信息"""
        return db.query(models.Dataset).options(
            joinedload(models.Dataset.owner) # <-- 使用 joinedload 加载 owner
        ).filter(models.Dataset.id == dataset_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        user: models.User,
        include_public: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[models.Dataset]:
        """
        获取数据集列表，并加载所有者信息。
        - 如果当前用户是管理员 (user.role == UserRole.admin)，则返回所有数据集。
        - 如果当前用户不是管理员：
            - 当 include_public 为 True 时，返回当前用户自己的数据集以及所有设置为公开的数据集。
            - 当 include_public 为 False (默认) 时，只返回当前用户自己的数据集。
        """
        query = db.query(models.Dataset).options(
            joinedload(models.Dataset.owner) # <-- 使用 joinedload 加载 owner
        )

        if user.role == models.UserRole.admin:
            pass
        elif include_public:
            query = query.filter(
                or_(
                    models.Dataset.owner_id == user.id,
                    models.Dataset.is_public == True
                )
            )
        else:
            query = query.filter(models.Dataset.owner_id == user.id)

        return query.offset(skip).limit(limit).all()


    def create_dataset(self, db: Session, dataset: dataset_schema.DatasetCreate, owner_id: int, storage_path: str) -> models.Dataset:
        """创建新的数据集记录"""
        db_dataset = models.Dataset(
            **dataset.model_dump(),
            owner_id=owner_id,
            storage_path=storage_path
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        return db_dataset


    def delete_dataset(self, db: Session, dataset_id: int) -> Optional[models.Dataset]:
        """
        删除数据集记录及其关联的文件夹。
        """
        db_dataset = self.get_dataset(db, dataset_id=dataset_id)
        if db_dataset:
            db.query(models.InferenceResult).filter(models.InferenceResult.source_dataset_id == dataset_id).delete(synchronize_session=False)
            # 1. 删除物理文件/文件夹
            storage_path = Path(db_dataset.storage_path)
            if storage_path.exists():
                print(f"Deleting dataset folder: {storage_path}")
                shutil.rmtree(storage_path)

            # 2. 从数据库删除记录
            db.delete(db_dataset)
            db.commit()
        return db_dataset

    def update_dataset_public_status(self, db: Session, dataset_id: int, is_public: bool) -> Optional[models.Dataset]:
        db_dataset = self.get_dataset(db, dataset_id=dataset_id)
        if db_dataset:
            db_dataset.is_public = is_public
            db.commit()
            db.refresh(db_dataset)
        return db_dataset

# 实例化 CRUDDataset 类，以便在其他模块中导入和使用
crud_dataset = CRUDDataset()
