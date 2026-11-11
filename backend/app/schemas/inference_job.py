from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from ..db.models import JobStatus

class InferenceJobCreate(BaseModel):
    job_name: str
    source_dataset_id: int
    model_id: int
    inference_params: Dict[str, Any] = Field({}, example={"image_size": 512, "threshold": 0.5})

class InferenceJob(BaseModel):
    id: int
    job_name: str
    source_dataset_id: int
    model_id: int
    status: JobStatus
    output_path: Optional[str]
    created_at: datetime
    results_summary: Optional[Dict[str, Any]]
    class Config: from_attributes = True