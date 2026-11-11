# app/services/model_runners/unet_cbam_runner.py

import torch
import cv2
import numpy as np
import albumentations as albu
from albumentations.pytorch import ToTensorV2
from typing import Dict, Any, Tuple

from app.services.model_runner import BaseModelRunner
from app.ml_models.unet_with_cbam import UNet


class UNetCBAMRunner(BaseModelRunner):
    def __init__(self, model_path: str, config: Dict = None):
        super().__init__(model_path, config)
        self.device = torch.device(self.config.get("device", "cuda" if torch.cuda.is_available() else "cpu"))
        print(f"UNet-CBAM model will run on device: {self.device}")
        self.image_size = self.config.get('image_size', 512)
        self.threshold = self.config.get('threshold', 0.5)
        self.transforms = albu.Compose([
            albu.Resize(height=self.image_size, width=self.image_size),
            albu.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
                max_pixel_value=255.0,
            ),
            ToTensorV2(),
        ])
        self.model = self.load_model()
        print(f"UNet-CBAM model loaded from {self.model_path} to {self.device}.")

    def load_model(self):
        model = UNet(in_channels=3, out_channels=1).to(self.device)
        try:
            checkpoint = torch.load(self.model_path, map_location=self.device)
        except FileNotFoundError:
            raise FileNotFoundError(f"Model file not found at {self.model_path}")
        state_dict = checkpoint.get("state_dict", checkpoint)
        new_state_dict = {}
        for k, v in state_dict.items():
            name = k[7:] if k.startswith('module.') else k
            new_state_dict[name] = v
        model.load_state_dict(new_state_dict)
        model.eval()
        return model

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        对输入图像进行预处理，使其符合 UNet-CBAM 模型的输入要求。
        Args:
            image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
        Returns:
            torch.Tensor: 预处理后的图像张量，准备好输入模型。
        """
        # 确保图像是 RGB 格式，因为 albumentations 默认处理 RGB 图像
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # 将 BGR 转换为 RGB

        augmented = self.transforms(image=image)
        input_tensor = augmented["image"].unsqueeze(0).to(self.device)
        return input_tensor

    def predict(self, processed_data: torch.Tensor) -> torch.Tensor:
        """
        使用 UNet-CBAM 模型进行预测。
        Args:
            processed_data (torch.Tensor): 预处理后的图像张量。
        Returns:
            torch.Tensor: 模型的原始预测结果（分割 logits）。
        """
        with torch.no_grad():
            prediction = self.model(processed_data)
        return prediction

    def postprocess(self, prediction: torch.Tensor, original_image: np.ndarray,
                    original_dims: Tuple[int, int]) -> np.ndarray:
        """
        对 UNet-CBAM 模型的预测结果进行后处理，阈值化，并将掩码缩放回原始图像尺寸。
        Args:
            prediction (torch.Tensor): 模型的原始预测结果。
            original_image (np.ndarray): 原始输入图像（OpenCV BGR 格式）。
            original_dims (Tuple[int, int]): 原始图像的尺寸 (高, 宽)。
        Returns:
            np.ndarray: 0-255 的单通道灰度掩码，缩放回原始尺寸。
        """
        preds = torch.sigmoid(prediction)
        preds = (preds > self.threshold).float()

        pred_mask = preds.squeeze().cpu().numpy()

        original_h, original_w = original_dims
        # 将掩码缩放回原始图像尺寸
        pred_mask_resized = cv2.resize(pred_mask, (original_w, original_h), interpolation=cv2.INTER_NEAREST)

        # 返回 0-255 的单通道灰度图
        return (pred_mask_resized * 255).astype(np.uint8)