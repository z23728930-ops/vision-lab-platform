import time
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any # 导入 Any

from ..core.config import settings
from .camera_service import camera_service
from ..crud.crud_dataset import crud_dataset
from ..db import models
from ..db.base import SessionLocal # 确保导入了SessionLocal


class AcquisitionService:
    def __init__(self):
        self.is_capturing_calibration_frames = False
        self.calibration_frames = []
        self.is_collecting_data = False
        self.data_collection_path: Optional[Path] = None
        self.data_collection_user_id: Optional[int] = None

    def start_calibration_capture(self):
        """开始捕捉用于标定的棋盘格帧"""
        if camera_service.is_active:
            self.is_capturing_calibration_frames = True
            self.calibration_frames = []
            print("Starting to capture calibration frames.")
            return True
        return False

    def capture_frame(self) -> bool:
        """捕捉单张棋盘格帧"""
        if self.is_capturing_calibration_frames:
            frame = camera_service.get_frame()
            if frame is not None:
                self.calibration_frames.append(frame)
                print(f"Captured a calibration frame. Total frames: {len(self.calibration_frames)}")
                return True
        return False

    def stop_and_calibrate(self, pattern_size: Tuple[int, int], square_size: float) -> Optional[Dict]:
        """停止捕捉并执行标定算法"""
        self.is_capturing_calibration_frames = False
        if not self.calibration_frames:
            print("No frames captured for calibration.")
            return None

        print(f"Starting calibration with {len(self.calibration_frames)} frames...")

        # 准备棋盘格的世界坐标
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        objp = objp * square_size

        objpoints = []  # 3d point in real world space
        imgpoints = []  # 2d points in image plane.

        # --- 修改开始 ---
        # 明确声明图像尺寸变量，并初始化为None
        image_size_for_calibration: Optional[Tuple[int, int]] = None
        # --- 修改结束 ---

        for frame in self.calibration_frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # --- 修改开始 ---
            # 仅在第一次获取到灰度图时记录其尺寸
            if image_size_for_calibration is None:
                image_size_for_calibration = gray.shape[::-1]
            # --- 修改结束 ---

            # 查找棋盘格角点
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

            if ret:
                objpoints.append(objp)
                # 提高角点精度
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                imgpoints.append(corners2)
                print("Found chessboard corners in a frame.")
            else:
                print("Could not find chessboard corners in a frame, skipping.")

        if not imgpoints:
            print("Could not find corners in any of the provided frames.")
            self.calibration_frames = []
            return None

        # --- 修改开始 ---
        # 在调用cv2.calibrateCamera前，断言 image_size_for_calibration 不为 None
        # 因为如果 imgpoints 不为空，那么 image_size_for_calibration 必然已被赋值
        assert image_size_for_calibration is not None, "Image size could not be determined from calibration frames."
        # --- 修改结束 ---

        # 执行相机标定
        # --- 修改：将 gray_frame_shape 替换为 image_size_for_calibration ---
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, image_size_for_calibration, None, None)

        if not ret:
            print("Calibration failed.")
            self.calibration_frames = []
            return None

        # 计算重投影误差
        mean_error = 0
        for i in range(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            mean_error += error

        rmse = np.sqrt(mean_error / len(objpoints))
        print(f"Calibration successful. RMSE: {rmse}")

        # 清理
        self.calibration_frames = []

        return {
            "camera_matrix": mtx.tolist(),
            "distortion_coefficients": dist.ravel().tolist(),
            "rmse": rmse
        }

    def start_data_collection(self, user_id: int, dataset_name: str):
        """开始采集数据，保存为新数据集"""
        if not camera_service.is_active:
            return False, "Camera is not active."
        if self.is_collecting_data:
            return False, "Already in data collection mode."

        folder_name = f"{dataset_name.replace(' ', '_')}_{int(time.time())}"
        storage_path = Path(settings.UPLOADS_DIR) / "datasets" / str(user_id) / folder_name
        storage_path.mkdir(parents=True, exist_ok=True)

        self.data_collection_path = storage_path
        self.data_collection_user_id = user_id
        self.is_collecting_data = True
        print(f"Starting data collection. Saving to: {storage_path}")
        return True, str(storage_path)

    def collect_data_frame(self):
        """在数据采集中时，捕获并保存一帧"""
        if not self.is_collecting_data:
            return

        frame = camera_service.get_frame()
        if frame is not None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            micros = f"{time.time():.6f}"[-6:]
            filename = f"frame_{timestamp}_{micros}.jpg"
            cv2.imwrite(str(self.data_collection_path / filename), frame)

    def capture_single_frame_to_dataset(self, dataset_id: int) -> Optional[str]:
        """
        捕获单帧并保存到已存在的数据集中。
        """
        if not camera_service.is_active:
            print("Cannot capture single frame: Camera is not active.")
            return None

        # 需要从数据库获取数据集的路径
        db = SessionLocal()
        try:
            dataset = crud_dataset.get_dataset(db, dataset_id=dataset_id)
            if not dataset:
                print(f"Cannot capture single frame: Dataset with ID {dataset_id} not found.")
                return None

            storage_path = Path(dataset.storage_path)
            frame = camera_service.get_frame()
            if frame is not None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                micros = f"{time.time():.6f}"[-6:]
                filename = f"single_capture_{timestamp}_{micros}.jpg"
                output_path = storage_path / filename
                cv2.imwrite(str(output_path), frame)
                db.add(models.Image(dataset_id=dataset_id, file_path=str(output_path), filename=filename))
                db.commit()
                print(f"Saved single frame to {output_path}")
                return str(output_path)
            else:
                print("Failed to get frame from camera.")
                return None
        finally:
            db.close()

    def stop_data_collection(self):
        """停止数据采集"""
        if not self.is_collecting_data:
            return None

        path_to_return = str(self.data_collection_path)
        print("Stopping data collection.")
        self.is_collecting_data = False
        self.data_collection_path = None
        self.data_collection_user_id = None
        return path_to_return

    def cancel_calibration_capture(self):
        """取消标定，清空已捕捉的帧"""
        self.is_capturing_calibration_frames = False
        self.calibration_frames = []
        print("Calibration cancelled.")


# 创建单例服务
acquisition_service = AcquisitionService()
