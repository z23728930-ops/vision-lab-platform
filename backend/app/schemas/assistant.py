from typing import Any, Optional

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AssistantChatResponse(BaseModel):
    reply: str
    intent: str
    dataset_id: Optional[int] = None
    model_id: Optional[int] = None
    confidence: Optional[float] = None
    job_id: Optional[int] = None
    status: Optional[str] = None
    data: Optional[Any] = None
