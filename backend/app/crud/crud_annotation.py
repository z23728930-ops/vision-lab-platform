# app/crud/crud_annotation.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db import models
from app.schemas.annotation import AnnotationCreate, AnnotationUpdate, Annotation as AnnotationSchema # 导入 AnnotationSchema 以避免命名冲突

class CRUDAnnotation:
    def get_annotation(self, db: Session, annotation_id: int) -> Optional[models.Annotation]:
        """通过ID获取单个标注"""
        return db.query(models.Annotation).filter(models.Annotation.id == annotation_id).first()

    def get_annotations_by_image(self, db: Session, image_id: int) -> List[models.Annotation]:
        """获取指定图片的所有标注"""
        return db.query(models.Annotation).filter(models.Annotation.image_id == image_id).all()

    def create_annotation(self, db: Session, annotation_in: AnnotationCreate) -> models.Annotation:
        """创建单个标注"""
        db_annotation = models.Annotation(
            image_id=annotation_in.image_id,
            dataset_id=annotation_in.dataset_id,
            annotation_type=annotation_in.annotation_type,
            label=annotation_in.label,
            coordinates=annotation_in.coordinates.model_dump(), # Pydantic v2 使用 model_dump()
            extra_data=annotation_in.extra_data
        )
        db.add(db_annotation)
        db.commit()
        db.refresh(db_annotation)
        return db_annotation

    def create_multiple_annotations(self, db: Session, annotations_in: List[AnnotationCreate]) -> List[models.Annotation]:
        """批量创建标注"""
        db_annotations = []
        for ann_in in annotations_in:
            db_annotations.append(models.Annotation(
                image_id=ann_in.image_id,
                dataset_id=ann_in.dataset_id,
                annotation_type=ann_in.annotation_type,
                label=ann_in.label,
                coordinates=ann_in.coordinates.model_dump(),
                extra_data=ann_in.extra_data
            ))
        db.add_all(db_annotations)
        db.commit()
        for ann in db_annotations:
            db.refresh(ann)
        return db_annotations

    def update_annotation(self, db: Session, annotation_id: int, annotation_update: AnnotationUpdate) -> Optional[models.Annotation]:
        """更新单个标注"""
        db_annotation = self.get_annotation(db, annotation_id)
        if db_annotation:
            update_data = annotation_update.model_dump(exclude_unset=True) # 只更新传入的字段
            for key, value in update_data.items():
                if key == "coordinates":
                    # 坐标可能是Pydantic模型，需要转换为字典
                    setattr(db_annotation, key, value.model_dump() if isinstance(value, BaseModel) else value)
                elif key == 'extra_data':
                    setattr(db_annotation,key,value)
                else:
                    setattr(db_annotation, key, value)
            db.add(db_annotation) # 标记为脏，以便 commit
            db.commit()
            db.refresh(db_annotation)
        return db_annotation

    def delete_annotation(self, db: Session, annotation_id: int) -> Optional[models.Annotation]:
        """删除单个标注"""
        db_annotation = self.get_annotation(db, annotation_id)
        if db_annotation:
            db.delete(db_annotation)
            db.commit()
        return db_annotation

    def delete_multiple_annotations(self, db: Session, annotation_ids: List[int]) -> int:
        """批量删除标注"""
        if not annotation_ids:
            return 0
        deleted_count = db.query(models.Annotation).filter(models.Annotation.id.in_(annotation_ids)).delete(synchronize_session=False)
        db.commit()
        return deleted_count

crud_annotation = CRUDAnnotation()