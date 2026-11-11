# app/schemas/annotation.py
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from ..db.models import AnnotationType # 导入 AnnotationType 枚举

# 坐标子Schema
class BboxCoordinates(BaseModel):
    x: float
    y: float
    width: float
    height: float

class PolygonCoordinates(BaseModel):
    points: List[List[float]] # [[x1, y1], [x2, y2], ...]

class PointCoordinates(BaseModel):
    x: float
    y: float

# 标注的基础属性
class AnnotationBase(BaseModel):
    image_id: int
    dataset_id: int
    annotation_type: AnnotationType
    label: str
    coordinates: Union[BboxCoordinates, PolygonCoordinates, PointCoordinates] # 使用 Union 允许不同类型
    extra_data: Dict[str, Any] = Field(default_factory=dict) # 默认为空字典

# 用于创建标注的Schema
class AnnotationCreate(AnnotationBase):
    pass

# 用于更新标注的Schema (部分更新)
class AnnotationUpdate(BaseModel):
    label: Optional[str] = None
    coordinates: Optional[Union[BboxCoordinates, PolygonCoordinates, PointCoordinates]] = None
    extra_data: Optional[Dict[str, Any]] = None

# 从数据库读取并返回给客户端的Schema
class Annotation(AnnotationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 批量操作的Schema
class AnnotationBatchCreate(BaseModel):
    annotations: List[AnnotationCreate]

class AnnotationBatchUpdate(BaseModel):
    annotations: List[Annotation] # 假设更新时会带上ID