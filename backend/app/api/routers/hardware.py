# app/api/routers/hardware.py

import asyncio
import json
import re
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union # <-- 新增 Union 导入

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends, Body, UploadFile, File
import cv2
import numpy as np

from ...crud.crud_dataset import crud_dataset
from ...db import models
from ...services.camera_service import camera_service
from ... import schemas # 确保 schemas 中包含了 CameraConnectRequest
from ...services.acquisition_service import acquisition_service
from ..deps import get_current_active_user
from ...db.base import get_db
from sqlalchemy.orm import Session

# --- 新增导入：模型运行器相关 ---
from ...services.model_runner import get_model_runner
from ...crud.crud_model import get_model as crud_get_model # 导入 crud_model 的 get_model 方法
# -------------------------------

router = APIRouter()

MAX_BROWSER_CAPTURE_BYTES = 12 * 1024 * 1024
ALLOWED_BROWSER_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/browser-capture/{dataset_id}", status_code=status.HTTP_201_CREATED)
async def upload_browser_capture(
        dataset_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
):
    """接收浏览器本地摄像头抓拍，并保存到当前用户拥有的数据集。"""
    dataset = crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "数据集不存在")
    if dataset.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权向该数据集写入图片")

    extension = ALLOWED_BROWSER_IMAGE_TYPES.get((file.content_type or "").lower())
    if not extension:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "仅支持 JPEG、PNG 或 WebP 图片")

    content = await file.read(MAX_BROWSER_CAPTURE_BYTES + 1)
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "抓拍图片为空")
    if len(content) > MAX_BROWSER_CAPTURE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "抓拍图片不能超过 12MB")

    image_array = np.frombuffer(content, dtype=np.uint8)
    decoded = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无法解析抓拍图片")

    storage_path = Path(dataset.storage_path)
    if not storage_path.is_absolute():
        storage_path = Path.cwd() / storage_path
    uploads_root = (Path.cwd() / "uploads").resolve()
    resolved_storage = storage_path.resolve()
    try:
        resolved_storage.relative_to(uploads_root)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "数据集目录不在允许的上传区域内")
    resolved_storage.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_id = re.sub(r"[^a-f0-9]", "", uuid.uuid4().hex)[:8]
    filename = f"browser_capture_{timestamp}_{safe_id}{extension}"
    output_path = resolved_storage / filename
    output_path.write_bytes(content)

    relative_path = output_path.relative_to(Path.cwd()).as_posix()
    db_image = models.Image(dataset_id=dataset_id, file_path=relative_path, filename=filename)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return {
        "message": "浏览器抓拍已保存",
        "image_id": db_image.id,
        "dataset_id": dataset_id,
        "filename": filename,
        "path": relative_path,
    }


@router.get("/cameras", response_model=List[Dict[str, Any]])
def list_available_cameras():
    """
    列出可用的相机 (模拟)。
    在真实场景中，这里会使用SDK来发现已连接的工业相机。
    """
    # 对于开发，设有一个默认摄像头。
    # 实际连接手机摄像头时，用户将直接输入URL，而非选择ID。
    return [{"id": 0, "name": "Default Webcam (ID 0)"}]


@router.post("/camera/connect") # MODIFIED: Removed path parameter {camera_id}
def connect_camera(request: schemas.CameraConnectRequest): # MODIFIED: Accepts request body with camera_source
    """连接到指定ID或URL的相机"""
    success = camera_service.connect(request.camera_source) # MODIFIED: Use request.camera_source
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to camera with source {request.camera_source}" # MODIFIED: Update detail message
        )
    return {"message": f"Successfully connected to camera {request.camera_source}"} # MODIFIED: Update message


@router.post("/camera/disconnect")
def disconnect_camera():
    """断开相机连接"""
    camera_service.disconnect()
    return {"message": "Camera disconnected."}

# --- 修改：获取相机当前连接状态的API端点 ---
@router.get("/camera/status")
def get_camera_status():
    """
    获取当前相机连接状态。
    """
    return {
        "is_connected": camera_service.is_active,
        "camera_source": camera_service.camera_source if camera_service.is_active else -1 # MODIFIED: Use camera_source
    }
# ---------------------------------------------


@router.get("/camera/parameters", response_model=List[schemas.CameraParameter])
def get_camera_parameters():
    """获取当前连接相机的所有可配置参数及其当前值"""
    if not camera_service.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Camera is not connected.")

    params = camera_service.get_all_parameters()
    return params


@router.put("/camera/parameters", response_model=Dict[str, bool])
def set_camera_parameters(config: schemas.CameraConfig):
    """批量设置相机参数"""
    if not camera_service.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Camera is not connected.")

    success = camera_service.set_multiple_parameters(
        [p.model_dump() for p in config.parameters]
    )
    return {"success": success}


@router.post("/calibration/start", status_code=status.HTTP_202_ACCEPTED)
def start_calibration():
    """开始捕捉用于标定的帧。相机会持续运行，等待捕捉指令。"""
    success = acquisition_service.start_calibration_capture()
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Camera not connected or already in calibration mode.")
    return {"message": "Calibration capture started. Send requests to /capture-frame to grab frames."}


@router.post("/calibration/capture", status_code=status.HTTP_201_CREATED)
def capture_calibration_frame():
    """捕捉一张用于标定的帧。"""
    success = acquisition_service.capture_frame()
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not in calibration mode or failed to capture frame.")
    return {"message": f"Frame captured. Total frames: {len(acquisition_service.calibration_frames)}"}


@router.post("/calibration/run", response_model=schemas.CalibrationResult)
def run_calibration(
        pattern_width: int = 9,
        pattern_height: int = 6,
        square_size_mm: float = 25.0
):
    """
    停止捕捉并使用已捕捉的帧运行标定算法。
    - pattern_width: 棋盘格内部角的宽度数量。
    - pattern_height: 棋盘格内部角的高度数量。
    - square_size_mm: 棋盘格方块的实际边长（毫米）。
    """
    result = acquisition_service.stop_and_calibrate((pattern_width, pattern_height), square_size_mm)
    if result is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Calibration failed. Not enough valid frames or corners not found.")
    return result


@router.post("/acquisition/start", status_code=status.HTTP_201_CREATED)
def start_acquisition(
        dataset_name: str,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    开始将实时视频帧采集为新的数据集。
    """
    success, message = acquisition_service.start_data_collection(current_user.id, dataset_name)
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    # 在数据库中为新数据集创建一个记录
    dataset_in = schemas.DatasetCreate(name=dataset_name, description=f"Live data acquisition.")
    crud_dataset.create_dataset(db, dataset=dataset_in, owner_id=current_user.id, storage_path=message)

    return {"message": "Data acquisition started.", "storage_path": message}


@router.post("/acquisition/capture-single/{dataset_id}")
def capture_single_frame(
        dataset_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    捕获单帧并将其添加到指定的数据集中。
    """
    # 验证数据集是否存在且属于当前用户
    dataset = crud_dataset.get_dataset(db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found.")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions for this dataset.")

    saved_path = acquisition_service.capture_single_frame_to_dataset(dataset_id=dataset_id)

    if not saved_path:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to capture or save frame.")

    return {"message": "Frame captured successfully", "path": saved_path}


@router.get("/camera/profiles", response_model=List[str])
def list_camera_profiles():
    return camera_service.list_profiles()

@router.post("/camera/profiles/{profile_name}/save")
def save_camera_profile(profile_name: str):
    success = camera_service.save_parameters_to_profile(profile_name)
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to save profile. Is camera connected?")
    return {"message": f"Profile '{profile_name}' saved successfully."}

@router.post("/camera/profiles/{profile_name}/load")
def load_camera_profile(profile_name: str):
    success = camera_service.load_parameters_from_profile(profile_name)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Profile '{profile_name}' not found or failed to apply.")
    return {"message": f"Profile '{profile_name}' loaded and applied."}

@router.post("/acquisition/stop")
def stop_acquisition():
    """停止数据采集。"""
    storage_path = acquisition_service.stop_data_collection()
    if storage_path is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not in data acquisition mode.")
    return {"message": "Data acquisition stopped.", "storage_path": storage_path}

# ...
@router.post("/calibration/cancel", status_code=status.HTTP_200_OK)
def cancel_calibration():
    """取消当前的标定流程"""
    acquisition_service.cancel_calibration_capture()
    return {"message": "Calibration cancelled."}

# --- 修改：camera_stream WebSocket 端点，支持实时推理 ---
@router.websocket("/camera/stream")
async def camera_stream(websocket: WebSocket, model_id: Optional[int] = None, inference_params: Optional[str] = None):
    """
    通过WebSocket实时传输相机视频流，并可选地叠加推理结果。
    - model_id: 如果提供，将使用该模型进行实时推理。
    - inference_params: 推理参数的JSON字符串，例如 '{"conf_threshold": 0.5, "image_size": 640}'。
    """
    await websocket.accept()
    print("WebSocket connection established for camera stream.")

    model_runner = None
    if model_id is not None:
        db = next(get_db()) # 获取数据库会话
        try:
            model = crud_get_model(db, model_id=model_id)
            if not model:
                await websocket.send_json({"error": f"Model with ID {model_id} not found."})
                await websocket.close(code=1008, reason=f"Model {model_id} not found.")
                return

            parsed_params = {}
            if inference_params:
                try:
                    parsed_params = json.loads(inference_params) # 解析JSON字符串
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid inference_params JSON."})
                    await websocket.close(code=1008, reason="Invalid inference_params.")
                    return

            model_runner = get_model_runner(model.model_type, model.file_path, parsed_params)
            print(f"Loaded model {model.name} (ID: {model_id}, Type: {model.model_type}) for real-time inference.")
        except Exception as e:
            print(f"Error loading model for real-time inference: {e}")
            await websocket.send_json({"error": f"Failed to load model: {e}"})
            await websocket.close(code=1008, reason=f"Failed to load model: {e}")
            return
        finally:
            db.close() # 关闭数据库会话

    try:
        while True:
            if not camera_service.is_active:
                print("Camera is not active. Closing WebSocket.")
                await websocket.close(code=1000, reason="Camera not active")
                break

            frame = camera_service.get_frame()
            if frame is not None:
                # 如果正在采集数据，则保存帧
                if acquisition_service.is_collecting_data:
                    # collect_data_frame 内部会获取当前帧并保存，不需要再次传递 frame
                    acquisition_service.collect_data_frame()

                # 如果加载了模型，则进行推理并叠加结果
                if model_runner:
                    try:
                        # 确保输入图像是彩色的，因为YOLO模型通常期望3通道
                        if len(frame.shape) == 2 or frame.shape[2] == 1:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        else:
                            frame_rgb = frame

                        # 运行推理
                        result_frame = model_runner.run(frame_rgb)
                        # 确保结果帧是可编码的图像格式 (例如BGR)
                        if result_frame is not None and result_frame.ndim == 3 and result_frame.shape[2] == 3:
                            frame_to_send = result_frame
                        else:
                            # 如果模型返回的不是预期的彩色图，退回到原始帧
                            print("Warning: Model runner returned unexpected frame format. Sending original frame.")
                            frame_to_send = frame_rgb
                    except Exception as e:
                        print(f"Error during real-time inference: {e}")
                        # 推理失败时，继续发送原始帧
                        frame_to_send = frame_rgb
                else:
                    frame_to_send = frame # 没有模型则发送原始帧

                # 将帧编码为JPEG格式
                ret, buffer = cv2.imencode('.jpg', frame_to_send, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    # 发送二进制数据
                    await websocket.send_bytes(buffer.tobytes())

            # 控制帧率，避免阻塞事件循环
            await asyncio.sleep(1 / 30)  # 约 30 FPS
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket.")
    except Exception as e:
        print(f"An error occurred in WebSocket: {e}")
    finally:
        print("WebSocket connection closed.")
        # 注意：我们在这里不自动断开相机连接，以便其他操作可以继续使用相机。
        # camera_service.disconnect()
