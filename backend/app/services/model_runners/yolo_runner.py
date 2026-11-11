# app/services/model_runners/yolo_runner.py

import torch
import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, Any, Tuple

from app.services.model_runner import BaseModelRunner

class YOLORunner(BaseModelRunner):
    def __init__(self, model_path: str, config: Dict = None):
        super().__init__(model_path, config)
        self.device = torch.device(self.config.get("device", "cuda" if torch.cuda.is_available() else "cpu"))
        print(f"YOLO model will run on device: {self.device}")
        self.image_size = self.config.get('image_size', 640)
        self.conf_threshold = self.config.get('conf_threshold', 0.25)
        self.iou_threshold = self.config.get('iou_threshold', 0.7)
        self.model = self.load_model()
        print(f"YOLO model loaded from {self.model_path} to {self.device}.")

    def load_model(self):
        try:
            model = YOLO(self.model_path)
            model.to(self.device)
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model from {self.model_path}: {e}")

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        对输入图像进行预处理，使其符合 YOLO 模型的输入要求。
        Args:
            image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
        Returns:
            np.ndarray: 预处理后的图像（BGR 格式），Ultralytics YOLO 可直接接受。
        """
        # 确保图像是BGR格式（OpenCV默认格式）
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif len(image.shape) == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        # 如果已经是3通道BGR，则无需转换
        return image

    def predict(self, processed_data: np.ndarray) -> Any:
        """
        使用 YOLO 模型进行预测。
        Args:
            processed_data (np.ndarray): 经过 preprocess 处理后的图像数据。
        Returns:
            Any: 模型的原始预测结果 (Ultralytics Results 对象列表)。
        """
        try:
            results = self.model.predict(
                source=processed_data,
                imgsz=self.image_size,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False
            )
            return results
        except Exception as e:
            raise RuntimeError(f"Error during YOLO model prediction: {str(e)}")

    def postprocess(self, prediction_results: Any, original_image: np.ndarray, original_dims: Tuple[int, int]) -> np.ndarray:
        """
        对 YOLO 模型的预测结果进行后处理，通过在原始图像上绘制边界框来可视化。
        Args:
            prediction_results (Any): YOLO 模型的原始预测结果 (Results 对象列表)。
            original_image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
            original_dims (Tuple[int, int]): 原始图像的尺寸 (高, 宽)。
        Returns:
            np.ndarray: 绘制了边界框和标签的图像。
        """
        try:
            if not prediction_results:
                # 如果没有检测结果，返回原始图像副本
                return original_image.copy()

            # Ultralytics 的 plot() 方法会直接在原始图像上绘制，并返回绘制后的图像
            # prediction_results[0].orig_img 理论上是原始图像，但为了与 BaseModelRunner 保持一致，
            # 这里的 original_image 参数是更可靠的原始图像来源。
            # 实际上，Ultralytics 的 plot() 内部会尝试获取原始图像，如果传入的是 np.ndarray，它会直接使用。
            annotated_frame = prediction_results[0].plot()
            return annotated_frame
        except Exception as e:
            print(f"Error during YOLO postprocessing: {str(e)}")
            # 出现错误时返回原始图像副本
            return original_image.copy()