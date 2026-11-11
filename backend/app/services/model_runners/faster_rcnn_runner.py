# app/services/model_runners/faster_rcnn_runner.py

import torch
import numpy as np
import cv2
from typing import Dict, Any, Tuple
import torchvision.ops as ops

from app.services.model_runner import BaseModelRunner
from app.ml_models.faster_rcnn_model import get_faster_rcnn_model
from app.ml_models.transforms import get_inference_transforms


# 辅助函数：在图像上绘制边界框和标签
def _draw_boxes_on_image(image: np.ndarray, detections: np.ndarray, class_names: Dict[int, str] = None) -> np.ndarray:
    """
    在图像上绘制边界框和标签。
    Args:
        image (np.ndarray): 原始图像 (BGR 格式)。
        detections (np.ndarray): 检测结果数组 [x1, y1, x2, y2, confidence, class_id]。
        class_names (Dict[int, str]): 可选的类别ID到类别名称的映射字典。
    Returns:
        np.ndarray: 绘制了边界框的图像。
    """
    annotated_image = image.copy()  # 在副本上绘制，不修改原始图像

    if class_names is None:
        # 默认类别名称，假设 1 是缺陷，0 是背景 (Faster R-CNN 通常从 1 开始计数类别)
        class_names = {1: "Defect"}

    for det in detections:
        x1, y1, x2, y2, score, class_id = det.astype(float)  # 保持浮点数，但转换为int用于绘图
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        label = class_names.get(int(class_id), f"Class {int(class_id)}")
        text = f"{label}: {score:.2f}"

        color = (0, 255, 0)  # 绿色边界框

        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
        # 放置文本，确保文本在图像边界内
        text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        text_x = x1
        text_y = y1 - 10
        if text_y < text_size[1] + 5:  # 如果文本太靠近顶部，则放在框内
            text_y = y1 + text_size[1] + 5

        cv2.putText(annotated_image, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return annotated_image


class FasterRCNNRunner(BaseModelRunner):
    def __init__(self, model_path: str, config: Dict = None):
        super().__init__(model_path, config)
        self.device = torch.device(self.config.get("device", "cuda" if torch.cuda.is_available() else "cpu"))
        self.image_size = self.config.get("image_size", 512)
        self.conf_threshold = self.config.get("conf_threshold", 0.3)
        self.nms_iou_threshold = self.config.get("nms_iou_threshold", 0.1)
        self.num_classes = self.config.get("num_classes", 2)  # 包括背景类
        self.transforms = get_inference_transforms(self.image_size)
        self.model = self.load_model()
        print(f"Faster R-CNN model loaded from {self.model_path} on {self.device}")

    def load_model(self):
        model = get_faster_rcnn_model(num_classes=self.num_classes, pretrained=False)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        if 'state_dict' in checkpoint:
            model.load_state_dict(checkpoint['state_dict'])
        else:
            model.load_state_dict(checkpoint)
        model.to(self.device)
        model.eval()
        return model

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        对输入图像进行预处理，使其符合 Faster R-CNN 模型的输入要求。
        Args:
            image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
        Returns:
            torch.Tensor: 预处理后的图像张量，准备好输入模型。
        """
        # 将 BGR 转换为 RGB，因为 albumentations 默认处理 RGB 图像
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        transformed = self.transforms(image=image_rgb)
        input_tensor = transformed['image'].unsqueeze(0).to(self.device)  # 添加 batch 维度
        return input_tensor

    def predict(self, processed_input: torch.Tensor) -> Any:
        """
        使用 Faster R-CNN 模型进行预测。
        Args:
            processed_input (torch.Tensor): 预处理后的图像张量。
        Returns:
            Any: 模型的原始预测结果（字典，包含 boxes, labels, scores）。
        """
        with torch.no_grad():
            outputs = self.model(processed_input)
        # Faster R-CNN 返回一个列表，每个元素对应一个批次中的图像。
        # 由于我们一次只处理一张图像 (unsqueeze(0))，所以取第一个元素。
        return outputs[0]

    def postprocess(self, prediction: Any, original_image: np.ndarray, original_dims: Tuple[int, int]) -> np.ndarray:
        """
        对 Faster R-CNN 的预测结果进行后处理，包括过滤、NMS、坐标缩放，
        并在原始图像上绘制边界框。
        Args:
            prediction (Any): 模型的原始预测结果。
            original_image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
            original_dims (Tuple[int, int]): 原始图像的尺寸 (高, 宽)。
        Returns:
            np.ndarray: 绘制了边界框和标签的图像。
        """
        original_h, original_w = original_dims

        boxes = prediction['boxes']
        labels = prediction['labels']
        scores = prediction['scores']

        # 根据置信度阈值过滤
        keep = scores > self.conf_threshold
        boxes_filtered = boxes[keep]
        labels_filtered = labels[keep]
        scores_filtered = scores[keep]

        # 应用非极大值抑制 (NMS)
        if len(boxes_filtered) > 0:
            nms_indices = ops.nms(boxes_filtered, scores_filtered, self.nms_iou_threshold)
            boxes_nms = boxes_filtered[nms_indices]
            labels_nms = labels_filtered[nms_indices]
            scores_nms = scores_filtered[nms_indices]
        else:
            # 如果没有检测结果，返回空张量
            boxes_nms = torch.empty((0, 4), device=self.device)
            labels_nms = torch.empty((0,), device=self.device, dtype=torch.int64)
            scores_nms = torch.empty((0,), device=self.device)

        # 反向缩放和填充，将边界框坐标转换回原始图像尺寸
        # `get_inference_transforms` 使用 LongestMaxSize 和 PadIfNeeded。
        # 1. 计算 LongestMaxSize 应用的实际缩放因子
        scale_ratio = min(self.image_size / original_w, self.image_size / original_h)

        # 2. 计算填充量 (在缩放后的图像上)
        # 缩放后的图像尺寸
        scaled_w = int(original_w * scale_ratio)
        scaled_h = int(original_h * scale_ratio)

        # 填充量
        pad_x = (self.image_size - scaled_w) / 2
        pad_y = (self.image_size - scaled_h) / 2

        final_detections = []
        for i in range(len(boxes_nms)):
            x_min_pred, y_min_pred, x_max_pred, y_max_pred = boxes_nms[i].cpu().numpy()

            # 1. 移除填充
            x_min_unpadded = x_min_pred - pad_x
            y_min_unpadded = y_min_pred - pad_y
            x_max_unpadded = x_max_pred - pad_x
            y_max_unpadded = y_max_pred - pad_y

            # 2. 反向缩放回原始尺寸
            x_min_original = x_min_unpadded / scale_ratio
            y_min_original = y_min_unpadded / scale_ratio
            x_max_original = x_max_unpadded / scale_ratio
            y_max_original = y_max_pred / scale_ratio  # 这里y_max_pred应该也是unpadded的，但上面写错了，修正

            # 修正：y_max_pred / scale_ratio 应该是 y_max_unpadded / scale_ratio
            y_max_original = y_max_unpadded / scale_ratio

            # 3. 确保坐标在原始图像边界内
            x_min_original = np.clip(x_min_original, 0, original_w)
            y_min_original = np.clip(y_min_original, 0, original_h)
            x_max_original = np.clip(x_max_original, 0, original_w)
            y_max_original = np.clip(y_max_original, 0, original_h)

            final_detections.append([
                float(x_min_original),
                float(y_min_original),
                float(x_max_original),
                float(y_max_original),
                float(scores_nms[i].item()),
                int(labels_nms[i].item())
            ])

        if not final_detections:
            # 如果没有检测结果，返回原始图像副本
            return original_image.copy()

        detections_array = np.array(final_detections, dtype=np.float32)

        # 在原始图像上绘制边界框
        annotated_image = _draw_boxes_on_image(original_image, detections_array)

        return annotated_image