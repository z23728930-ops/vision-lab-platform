import re
from typing import Optional

from sqlalchemy.orm import Session

from .. import crud
from ..db import models
from ..schemas.inference_job import InferenceJobCreate
from ..services.inference_runner import run_inference_job
from pathlib import Path
import time


def _confidence(message: str) -> float:
    match = re.search(r"(?:置信度|阈值|confidence)[^0-9]{0,12}(0(?:\.\d+)?|1(?:\.0+)?)", message, re.I)
    if match:
        return float(match.group(1))
    return 0.5


def _find_by_name(items, message: str, user: Optional[models.User] = None):
    """Match a dataset name; prefer the current user's copy when duplicates exist."""
    named = [item for item in items if item.name and item.name.lower() in message.lower()]
    if not named:
        return None
    owned = [item for item in named if user is not None and item.owner_id == user.id]
    candidates = owned or named
    for item in candidates:
        path = Path(item.storage_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists() and any(path.rglob(ext) for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff")):
            return item
    return candidates[0]


def handle_message(db: Session, user: models.User, message: str, background_tasks=None) -> dict:
    text = message.strip()
    lower = text.lower()
    faq = _local_faq(text)
    if faq:
        return {"reply": faq, "intent": "local_help"}
    status_match = re.search(r"(?:任务|job)\s*#?\s*(\d+).*(?:状态|进度|结果)", text, re.I)
    if status_match:
        job_id = int(status_match.group(1))
        job = crud.crud_inference.get_inference_job(db, job_id)
        if not job or job.created_by_id != user.id:
            return {"reply": f"找不到任务 {job_id}，或你没有查看权限。", "intent": "job_not_found", "job_id": job_id}
        summary = job.results_summary if isinstance(job.results_summary, dict) else {}
        progress = summary.get("progress", 0); processed = summary.get("images_processed", 0)
        if job.status == models.JobStatus.completed:
            reply = f"任务 {job_id} 已完成，共处理 {processed} 张图片，进度 100%。可以点击查看结果。"
        elif job.status == models.JobStatus.failed:
            reply = f"任务 {job_id} 执行失败：{summary.get('error', '未知错误')}"
        else:
            reply = f"任务 {job_id} 当前状态为 {job.status.value}，已处理 {processed} 张图片，进度 {progress}%。"
        return {"reply": reply, "intent": "job_status", "job_id": job_id, "status": job.status.value, "data": summary}
    if any(word in text for word in ("有哪些数据集", "数据集列表", "可用数据集")):
        datasets = crud.crud_dataset.get_multi(db, user=user, include_public=True)
        return {"reply": "可用数据集：" + ("、".join(d.name for d in datasets) if datasets else "暂无"), "intent": "list_datasets", "data": [{"id": d.id, "name": d.name} for d in datasets]}
    if any(word in text for word in ("有哪些模型", "模型列表", "可用模型")):
        models_list = crud.crud_model.get_models(db)
        return {"reply": "可用模型：" + ("、".join(m.name for m in models_list) if models_list else "暂无"), "intent": "list_models", "data": [{"id": m.id, "name": m.name, "model_type": m.model_type} for m in models_list]}
    if any(word in text for word in ("检测", "推理", "质检")):
        datasets = crud.crud_dataset.get_multi(db, user=user, include_public=True)
        dataset = _find_by_name(datasets, text, user)
        if not dataset:
            return {"reply": "没有匹配到数据集，请先输入“有哪些数据集”查看可用数据集名称。", "intent": "need_dataset"}
        dataset_path = Path(dataset.storage_path)
        if not dataset_path.is_absolute():
            dataset_path = Path.cwd() / dataset_path
        image_count = sum(1 for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff") for _ in dataset_path.rglob(ext)) if dataset_path.exists() else 0
        if image_count == 0:
            return {"reply": f"数据集“{dataset.name}”（ID {dataset.id}）当前没有可读取的图片，无法创建推理任务。请先上传图片，或选择有图片的数据集。", "intent": "empty_dataset", "dataset_id": dataset.id, "data": {"image_count": 0, "storage_path": str(dataset_path)}}
        models_list = crud.crud_model.get_models(db)
        model = next((m for m in models_list if m.name and m.name.lower() in lower), None)
        if model is None:
            # Known dataset/model pairings from the supplied project. This is
            # deliberately conservative; unknown datasets still require an
            # explicit model to avoid silently running the wrong architecture.
            preferred_names = {
                "qk": ("qk",),
                "coco_for_yolov8n": ("yolo8n", "yolov8n"),
                "test_312": ("my-test-unet", "unet_test"),
            }.get(dataset.name.lower(), ())
            model = next((m for name in preferred_names for m in models_list if m.name and m.name.lower() == name), None)
        if model is None and len(models_list) == 1:
            model = models_list[0]
        if not model:
            return {"reply": f"数据集“{dataset.name}”有 {image_count} 张图片，但存在多个模型。请明确指定模型；可输入“有哪些模型”查看列表。", "intent": "need_model", "dataset_id": dataset.id, "data": {"image_count": image_count, "recommended": list(preferred_names) if 'preferred_names' in locals() else []}}
        model_path = Path(model.file_path)
        if not model_path.is_absolute():
            model_path = Path.cwd() / model_path
        if not model_path.exists():
            return {"reply": f"模型文件不存在，无法推理。请在模型管理中重新上传模型文件。", "intent": "invalid_model", "dataset_id": dataset.id, "model_id": model.id, "data": {"model_path": str(model_path)}}
        threshold = _confidence(text)
        job_in = InferenceJobCreate(job_name=f"AI助手-{dataset.name}", source_dataset_id=dataset.id, model_id=model.id, inference_params={"confidence": threshold, "threshold": threshold})
        output_path = Path("uploads") / "inference_results" / f"AI助手_{int(time.time())}"
        job = crud.crud_inference.create_inference_job(db, job_in=job_in, user_id=user.id, output_path=str(output_path))
        if background_tasks is not None:
            background_tasks.add_task(run_inference_job, job_id=job.id, source_dataset_path=dataset.storage_path, model_path=model.file_path, model_type=model.model_type, output_path=str(output_path), params=job_in.inference_params)
        return {"reply": f"已识别需求，已创建推理任务：数据集“{dataset.name}”（{image_count}张图片），模型“{model.name}”（{model.model_type}），置信度阈值 {threshold:.2f}。", "intent": "create_inference_job", "dataset_id": dataset.id, "model_id": model.id, "confidence": threshold, "job_id": job.id, "status": job.status.value if hasattr(job.status, 'value') else str(job.status), "data": {"image_count": image_count, "model_type": model.model_type}}
    return {"reply": "我可以帮你查询数据集、查询模型，或创建缺陷检测任务。", "intent": "help"}


def _local_faq(message: str) -> Optional[str]:
    """实验课固定知识库：答案稳定、可复现，不依赖外部网络或大模型。"""
    text = message.lower()
    if any(k in text for k in ("什么是推理", "推理是什么", "推理含义")):
        return "推理就是让已经训练好的视觉模型分析新图片，并返回缺陷位置、类别和置信度。它不是重新训练模型。"
    if any(k in text for k in ("数据集为什么", "数据集为空", "空数据集")):
        return "数据集必须包含可读取的图片。数据集为空时，系统没有输入图片，无法创建有效的推理任务。请先上传图片并确认图片数量大于0。"
    if any(k in text for k in ("置信度", "阈值")):
        return "置信度阈值表示系统接受检测结果的最低可信程度。阈值较低通常能保留更多候选缺陷，但误检可能增加；阈值较高结果更严格，但可能漏检。建议用同一数据集对比不同阈值。"
    if any(k in text for k in ("yolo", "faster r-cnn", "faster_rcnn", "unet")):
        return "YOLO适合速度要求较高的目标检测，Faster R-CNN更适合精度要求较高的目标检测，UNet主要用于像素级分割。模型必须与任务类型和数据集标注方式匹配。"
    if any(k in text for k in ("单图", "批量", "在线推理", "视频流")):
        return "单图推理适合快速验证一张图片，批量推理适合处理数据集中的多张图片，在线推理适合摄像头采集场景。公网普通HTTP页面可能受到浏览器摄像头权限限制。"
    if any(k in text for k in ("失败", "报错", "排查")):
        return "推理失败时先检查四项：数据集是否存在且图片数量大于0，模型文件是否存在，模型与数据集是否匹配，任务参数是否有效。然后打开任务详情查看失败原因。"
    if any(k in text for k in ("报告", "导出", "json", "csv")):
        return "任务完成后可在推理任务详情查看结果图片和结构化报告。JSON适合系统读取，CSV适合表格分析和提交实验记录。"
    if any(k in text for k in ("训练", "模型上传", "本地训练")):
        return "本实验系统当前重点支持已有模型登记、上传和推理验证。若在本地完成训练，请将模型文件上传到模型管理，并填写模型类型、名称和适用场景后再创建推理任务。"
    if any(k in text for k in ("实验报告", "实验记录", "总结")):
        return "实验记录建议包含数据集、图片数量、模型、模型类型、置信度、任务ID、任务状态、检测结果、推理耗时，以及对阈值和检测结果的分析。"
    return None
