# app/schemas/image.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ImageBase(BaseModel):
    dataset_id: int
    file_path: str # 图片在服务器上的绝对路径
    filename: str  # 原始文件名

class ImageCreate(ImageBase):
    pass

class Image(ImageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True