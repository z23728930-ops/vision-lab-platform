from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ModelBase(BaseModel):
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    model_type: str = Field(..., example="unet_cbam")

class ModelCreate(ModelBase):
    pass

class Model(ModelBase):
    id: int
    file_path: str
    uploaded_by_id: int
    uploaded_by_username: Optional[str] = None
    created_at: datetime
    is_deleted: bool
    file_exists: bool = False
    class Config: from_attributes = True
