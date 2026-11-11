from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.schemas import User


# Dataset的基础属性
class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

# 创建时从API接收的属性 (通过表单)
class DatasetCreate(DatasetBase):
    pass

# 从数据库读取并返回给客户端的属性
class Dataset(DatasetBase):
    id: int
    owner_id: int
    storage_path: str
    created_at: datetime
    owner:User
    image_count: int = 0
    path_exists: bool = False
    ready_for_inference: bool = False
    annotated_image_count: int = 0
    reviewed_image_count: int = 0
    unreviewed_image_count: int = 0
    annotation_progress: float = 0.0

    class Config:
        from_attributes = True
