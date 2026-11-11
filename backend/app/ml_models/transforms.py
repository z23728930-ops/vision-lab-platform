# app/ml_models/transforms.py

import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2
import cv2

def get_inference_transforms(image_size: int):
    """
    获取用于推理的图像变换。
    Args:
        image_size (int): 图像将被缩放到的目标尺寸。
    Returns:
        albumentations.Compose: 图像变换组合。
    """
    return A.Compose([
        A.LongestMaxSize(max_size=image_size, interpolation=cv2.INTER_LINEAR),
        # 尝试将 'value' 改为 'fill_value' 以解决警告
        A.PadIfNeeded(min_height=image_size, min_width=image_size, border_mode=cv2.BORDER_CONSTANT, fill_value=0),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2()
    ])