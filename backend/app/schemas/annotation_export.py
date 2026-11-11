# app/schemas/annotation_export.py
from pydantic import BaseModel
from typing import Optional, List
import enum

class AnnotationExportFormat(str, enum.Enum):
    """定义支持的标注导出格式"""
    YOLO = "yolo"          # YOLOv5/v7 (bbox) 或 YOLOv8 (segmentation)
    PASCAL_VOC = "pascal_voc" # 边界框
    COCO = "coco"          # 边界框和分割

class AnnotationExportRequest(BaseModel):
    """标注导出请求的Schema"""
    format: AnnotationExportFormat
    include_images: bool = True # 是否包含图片文件在ZIP包中