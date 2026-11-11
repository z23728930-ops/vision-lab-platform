from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from typing import List, Any
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import time

from ... import crud, schemas
from ...core.config import settings
from ...db import models
from ...db.base import get_db
from ..deps import get_current_active_user

router = APIRouter()


@router.post("/upload", response_model=schemas.Model)
def upload_model(
        *,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
        name: str = Form(...),
        model_type: str = Form(...),
        version: str = Form(None),
        description: str = Form(""),
        file: UploadFile = File(...)
):
    allowed_extensions = (".pt", ".pth", ".tar", ".pth.tar", ".onnx")
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "仅支持 .pt、.pth、.tar、.pth.tar 和 .onnx 模型文件。")
    models_dir = Path(settings.UPLOADS_DIR) / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    file_location = models_dir / f"{int(time.time())}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    model_in = schemas.ModelCreate(name=name, model_type=model_type, version=version, description=description)
    new_model = crud.create_model(db, model=model_in, file_path=str(file_location), user_id=current_user.id)
    return new_model


@router.get("/", response_model=List[schemas.Model])
def read_models(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user), skip: int = 0, limit: int = 100):
    result = []
    for model in crud.get_models(db, skip=skip, limit=limit):
        path = Path(model.file_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        result.append({"id": model.id, "name": model.name, "version": model.version, "description": model.description, "model_type": model.model_type, "file_path": model.file_path, "uploaded_by_id": model.uploaded_by_id, "uploaded_by_username": model.uploader.username if model.uploader else None, "created_at": model.created_at, "is_deleted": model.is_deleted, "file_exists": path.exists()})
    return result


@router.delete("/{model_id}", response_model=schemas.Model)
def delete_existing_model(model_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    model = crud.get_model(db, model_id=model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found.")
    if current_user.role != models.UserRole.admin and model.uploaded_by_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能删除自己上传的模型。")
    deleted_model = crud.delete_model(db, model_id=model_id)
    if not deleted_model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found.")
    return deleted_model
