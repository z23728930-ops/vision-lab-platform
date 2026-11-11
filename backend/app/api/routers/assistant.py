from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from ...db.base import get_db
from ...db import models
from ...schemas.assistant import AssistantChatRequest, AssistantChatResponse
from ...api.deps import get_current_active_user
from ...services.assistant_service import handle_message
from ... import crud

router = APIRouter()
_SESSION = {}


@router.post("/chat", response_model=AssistantChatResponse)
def chat(request: AssistantChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Keep a small per-user context so follow-up messages such as “开始” or
    # “查询刚才的任务” can reuse the previous dataset/model/job.
    state = _SESSION.setdefault(current_user.id, {})
    msg = request.message.strip()
    low = msg.lower()
    if state.get("dataset_name") and not any(k in low for k in ("dataset", "数据集")):
        msg = f"{msg} {state['dataset_name']}"
    if state.get("model_name") and any(k in low for k in ("开始", "确认", "执行", "检测", "推理")) and not any(k in low for k in ("模型", "model")):
        msg = f"检测 {msg} {state['model_name']}"
    if state.get("job_id") and any(k in low for k in ("刚才", "这个任务", "任务状态", "进度")) and not any(ch.isdigit() for ch in msg):
        msg = f"查询任务 {state['job_id']} 状态"
    result = handle_message(db, current_user, msg, background_tasks)
    if result.get("dataset_id"):
        state["dataset_id"] = result["dataset_id"]
    data = result.get("data") or {}
    if result.get("intent") == "create_inference_job":
        state.update({"job_id": result.get("job_id"), "model_id": result.get("model_id"), "confidence": result.get("confidence")})
    if result.get("model_id"):
        state["model_id"] = result["model_id"]
    # Resolve names from the current response when available.
    if result.get("intent") in ("create_inference_job", "need_model") and result.get("dataset_id"):
        ds = db.query(models.Dataset).filter(models.Dataset.id == result["dataset_id"]).first()
        if ds: state["dataset_name"] = ds.name
    if result.get("intent") == "create_inference_job" and result.get("model_id"):
        mdl = db.query(models.Model).filter(models.Model.id == result["model_id"]).first()
        if mdl: state["model_name"] = mdl.name
    # 实验课使用可复现的本地知识库回答，不调用外部大模型或消耗 API 配额。
    # 业务查询和任务创建仍由 assistant_service 处理。
    return result
