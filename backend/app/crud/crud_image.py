# app/crud/crud_image.py
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import models # 确保这里的导入路径正确
from app.schemas.image import ImageCreate # 导入 ImageCreate Schema

class CRUDImage:
    def get_image(self, db: Session, image_id: int) -> Optional[models.Image]:
        """通过ID获取单个图片记录"""
        return db.query(models.Image).filter(models.Image.id == image_id).first()

    def get_images_by_dataset(self, db: Session, dataset_id: int, skip: int = 0, limit: int = 100) -> List[models.Image]:
        """获取特定数据集的所有图片记录"""
        return db.query(models.Image).filter(models.Image.dataset_id == dataset_id).offset(skip).limit(limit).all()

    def create_image(self, db: Session, image_in: ImageCreate) -> models.Image:
        """创建新的图片记录"""
        db_image = models.Image(
            dataset_id=image_in.dataset_id,
            file_path=image_in.file_path,
            filename=image_in.filename
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        return db_image

    def create_multiple_images(self, db: Session, images_in: List[ImageCreate]) -> List[models.Image]:
        """批量创建图片记录"""
        db_images = [
            models.Image(dataset_id=img.dataset_id, file_path=img.file_path, filename=img.filename)
            for img in images_in
        ]
        db.add_all(db_images)
        db.commit()
        for img in db_images:
            db.refresh(img)
        return db_images

    def delete_image(self, db: Session, image_id: int) -> Optional[models.Image]:
        """删除单个图片记录及其关联的标注 (通过级联删除)"""
        db_image = self.get_image(db, image_id)
        if db_image:
            db.delete(db_image)
            db.commit()
        return db_image

    def delete_images_by_dataset(self, db: Session, dataset_id: int) -> int:
        """删除特定数据集的所有图片记录及其关联的标注 (通过级联删除)"""
        deleted_count = db.query(models.Image).filter(models.Image.dataset_id == dataset_id).delete(synchronize_session=False)
        db.commit()
        return deleted_count

crud_image = CRUDImage()