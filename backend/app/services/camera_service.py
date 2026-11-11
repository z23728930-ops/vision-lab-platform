import json
from pathlib import Path

import cv2
from typing import List, Dict, Any, Optional, Union

from app.core.config import settings


class CameraService:
    _instance = None

    cap: Optional[cv2.VideoCapture]
    is_active: bool
    camera_source: Union[str, int]
    param_map: Dict[str, Any]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraService, cls).__new__(cls)
            cls._instance.cap = None
            cls._instance.is_active = False
            cls._instance.camera_source = -1
            cls._instance.param_map = {
    "亮度": (cv2.CAP_PROP_BRIGHTNESS, 0, 255, 1),  #(Brightness)
    "对比度": (cv2.CAP_PROP_CONTRAST, 0, 255, 1),  #(Contrast)
    "饱和度": (cv2.CAP_PROP_SATURATION, 0, 255, 1), #
    "色调": (cv2.CAP_PROP_HUE, -180, 180, 1), #(Hue)
    "增益": (cv2.CAP_PROP_GAIN, 0, 255, 1), #Gain
    "曝光": (cv2.CAP_PROP_EXPOSURE, -13, -1, 1), #(Exposure)
    "帧宽度": (cv2.CAP_PROP_FRAME_WIDTH, 320, 1920, 160),   #(Frame Width)
    "帧高度": (cv2.CAP_PROP_FRAME_HEIGHT, 240, 1080, 120), #(Frame Height)
    "帧率": (cv2.CAP_PROP_FPS, 5, 60, 5), #(FPS)
}
        return cls._instance

    def connect(self, camera_source: Union[str, int]) -> bool:
        """
        连接到指定的相机源。
        camera_source 可以是整数ID（本地摄像头）或字符串URL（网络摄像头）。
        """
        if self.is_active and self.camera_source == camera_source:
            print(f"Camera already connected to {camera_source}.")
            return True

        if self.is_active:
            print(f"Disconnecting from previous camera {self.camera_source} to connect to {camera_source}.")
            self.disconnect()

        print(f"Attempting to connect to camera source: {camera_source}")

        # --- 关键修改在这里：根据 camera_source 的类型来决定是否使用 CAP_DSHOW ---
        if isinstance(camera_source, int):
            # 如果是整数ID，继续使用 CAP_DSHOW 以获得更好的本地摄像头兼容性
            self.cap = cv2.VideoCapture(camera_source, cv2.CAP_DSHOW)
        else:
            # 如果是字符串URL，不指定后端，让OpenCV自动识别（通常会使用FFmpeg）
            self.cap = cv2.VideoCapture(camera_source)
        # ----------------------------------------------------------------------

        if self.cap.isOpened():
            self.is_active = True
            self.camera_source = camera_source
            print(f"Successfully connected to camera source: {camera_source}")
            return True
        else:
            print(f"Failed to open camera source: {camera_source}")
            self.disconnect()
            return False

    def disconnect(self):
        if self.is_active and self.cap:
            self.cap.release()
        self.cap = None
        self.is_active = False
        self.camera_source = -1

    def get_frame(self):
        if not self.is_active or not self.cap:
            return None
        ret, frame = self.cap.read()
        return frame if ret else None

    def get_all_parameters(self) -> List[Dict[str, Any]]:
        if not self.is_active or not self.cap:
            return []

        params_list = []
        for name, (key, min_val, max_val, step) in self.param_map.items():
            current_value = self.cap.get(key)
            params_list.append({
                "name": name,
                "key": key,
                "value": current_value,
                "min_value": min_val,
                "max_value": max_val,
                "step": step,
                "type": "slider" if name not in ["Frame Width", "Frame Height", "FPS"] else "input"
            })
        return params_list

    def set_parameter(self, key: int, value: float) -> bool:
        if not self.is_active or not self.cap:
            return False

        print(f"Setting parameter {key} to {value}")
        return self.cap.set(key, value)

    def set_multiple_parameters(self, params: List[Dict[str, Any]]) -> bool:
        if not self.is_active or not self.cap:
            return False

        all_success = True
        for param in params:
            key = param.get("key")
            value = param.get("value")
            if key is not None and value is not None:
                if not self.set_parameter(key, value):
                    all_success = False
        return all_success

    def save_parameters_to_profile(self, profile_name: str) -> bool:
        if not self.is_active: return False

        profiles_dir = Path(settings.UPLOADS_DIR) / "camera_profiles"
        profiles_dir.mkdir(exist_ok=True)

        current_params = self.get_all_parameters()
        file_path = profiles_dir / f"{profile_name}.json"

        with open(file_path, 'w') as f:
            json.dump(current_params, f, indent=4)
        print(f"Camera parameters saved to {file_path}")
        return True

    def load_parameters_from_profile(self, profile_name: str) -> bool:
        if not self.is_active: return False

        file_path = Path(settings.UPLOADS_DIR) / "camera_profiles" / f"{profile_name}.json"
        if not file_path.exists():
            print(f"Profile file not found: {file_path}")
            return False

        try:
            with open(file_path, 'r') as f:
                params_to_load = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from profile {file_path}: {e}")
            return False

        config_to_set = [{"key": p["key"], "value": p["value"]} for p in params_to_load]
        success = self.set_multiple_parameters(config_to_set)
        if success:
            print(f"Camera parameters loaded from {file_path}")
        else:
            print(f"Failed to load all parameters from {file_path}")
        return success

    def list_profiles(self) -> List[str]:
        profiles_dir = Path(settings.UPLOADS_DIR) / "camera_profiles"
        if not profiles_dir.exists(): return []

        profiles = [p.stem for p in profiles_dir.glob("*.json")]
        return profiles


camera_service = CameraService()