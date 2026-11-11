from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..db.models import JobStatus
from datetime import datetime

# 定义单个处理步骤的结构
class ProcessingStep(BaseModel):
    type: str = Field(..., example="gaussian_blur")
    params: Dict[str, Any] = Field({}, example={"kernel_size": 5})

# 创建一个新任务时API接收的数据
class ProcessingJobCreate(BaseModel):
    source_dataset_id: int
    output_name: str
    processing_steps: List[ProcessingStep]

# 从数据库读取并返回给客户端的任务信息
class ProcessingJob(BaseModel):
    id: int
    source_dataset_id: int
    output_folder_name: str
    status: JobStatus
    progress: int
    submitted_by_id: int
    created_at: datetime
    processing_steps: Optional[List[ProcessingStep]] # 使其可选，因为JSON字段可能为空

    class Config:
        from_attributes = True