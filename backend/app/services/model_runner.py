# app/services/model_runner.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import numpy as np


class BaseModelRunner(ABC):
    def __init__(self, model_path: str, config: Dict[str, Any] = None):
        self.model_path = model_path
        self.config = config or {}
        self.model = None # 模型实例现在由子类在 __init__ 中负责加载

    @abstractmethod
    def load_model(self):
        """
        加载模型并返回模型实例。
        子类应在此方法中实现具体的模型加载逻辑。
        """
        raise NotImplementedError

    @abstractmethod
    def preprocess(self, image: np.ndarray) -> Any:
        """
        对输入图像进行预处理，使其符合模型的输入要求。
        Args:
            image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
        Returns:
            Any: 预处理后的数据，可以直接传递给 predict 方法。
        """
        raise NotImplementedError

    @abstractmethod
    def predict(self, processed_data: Any) -> Any:
        """
        使用模型进行预测。
        Args:
            processed_data (Any): 经过 preprocess 处理后的数据。
        Returns:
            Any: 模型的原始预测结果。
        """
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, prediction: Any, original_image: np.ndarray, original_dims: Tuple[int, int]) -> np.ndarray:
        """
        对模型的预测结果进行后处理，并生成最终的可视化输出。
        Args:
            prediction (Any): 模型的原始预测结果。
            original_image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
            original_dims (Tuple[int, int]): 原始图像的尺寸 (高, 宽)。
        Returns:
            np.ndarray: 最终的可视化输出图像（例如，带有检测框的图像或分割掩码）。
        """
        raise NotImplementedError

    def run(self, image: np.ndarray) -> np.ndarray:
        """
        执行完整的推理流程：预处理 -> 预测 -> 后处理。
        Args:
            image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
        Returns:
            np.ndarray: 最终的可视化输出图像。
        """
        # 复制原始图像和获取尺寸，以便在后处理中使用
        original_image_bgr = image.copy()
        original_h, original_w = image.shape[:2]

        # 预处理
        processed_data = self.preprocess(image)

        # 预测
        prediction = self.predict(processed_data)

        # 后处理并生成可视化结果
        result_image = self.postprocess(prediction, original_image_bgr, (original_h, original_w))
        return result_image


def get_model_runner(model_type: str, model_path: str, config: Dict = None) -> BaseModelRunner:
    """工厂函数，根据模型类型返回对应的Runner实例"""
    if config is None:
        config = {}

    model_type_lower = model_type.lower()

    if model_type_lower == 'unet_cbam':
        from .model_runners.unet_cbam_runner import UNetCBAMRunner
        return UNetCBAMRunner(model_path, config)
    elif model_type_lower == 'yolo':
        from .model_runners.yolo_runner import YOLORunner
        return YOLORunner(model_path, config)
    elif model_type_lower == 'faster_rcnn':
        from .model_runners.faster_rcnn_runner import FasterRCNNRunner
        return FasterRCNNRunner(model_path, config)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")