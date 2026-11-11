# app/services/annotation_exporter.py
import os
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import json

from sqlalchemy.orm import Session
from PIL import Image as PILImage

from app.core.config import settings
from app.db import models
from app.schemas.annotation_export import AnnotationExportFormat
from app.crud.crud_dataset import crud_dataset
from app.crud.crud_image import crud_image
from app.crud.crud_annotation import crud_annotation


class AnnotationExporter:
    def __init__(self):
        # 类别映射：用于 YOLO 和 COCO 格式，需要将字符串标签映射为整数ID
        # 实际应用中，这个映射应该从数据库或配置文件中动态加载和管理
        self.label_to_id_map: Dict[str, int] = {}
        self.next_class_id = 0  # 用于动态分配类别ID

    def _get_class_id(self, label: str) -> int:
        """获取或创建类别的整数ID"""
        if label not in self.label_to_id_map:
            self.label_to_id_map[label] = self.next_class_id
            self.next_class_id += 1
        return self.label_to_id_map[label]

    def _reset_class_map(self):
        """在每次导出前重置类别映射，确保ID从0开始且与当前数据集相关"""
        self.label_to_id_map = {}
        self.next_class_id = 0

    def export_annotations(
            self,
            db: Session,
            dataset_id: int,
            export_format: AnnotationExportFormat,
            include_images: bool = True  # 是否包含图片文件在ZIP包中
    ) -> Optional[str]:
        """
        导出指定数据集的标注数据为指定格式的ZIP包。
        返回生成的ZIP文件的绝对路径。
        """
        self._reset_class_map()  # 每次导出前重置类别映射

        dataset = crud_dataset.get_dataset(db, dataset_id=dataset_id)
        if not dataset:
            return None

        images = crud_image.get_images_by_dataset(db, dataset_id=dataset_id)
        if not images:
            print(f"Dataset {dataset_id} has no images to export.")
            return None

        # 创建临时导出目录
        export_base_dir = Path(settings.UPLOADS_DIR) / "temp_exports"
        export_base_dir.mkdir(parents=True, exist_ok=True)

        temp_export_folder_name = f"dataset_{dataset_id}_annotations_{export_format.value}_{int(time.time())}"
        temp_export_path = export_base_dir / temp_export_folder_name
        temp_export_path.mkdir(parents=True, exist_ok=False)

        print(
            f"Starting export for dataset {dataset_id} to {temp_export_path} in {export_format.value} format. Include images: {include_images}")

        try:
            if export_format == AnnotationExportFormat.YOLO:
                self._export_to_yolo(db, images, temp_export_path, include_images)
            elif export_format == AnnotationExportFormat.PASCAL_VOC:
                self._export_to_pascal_voc(db, images, temp_export_path, include_images)
            elif export_format == AnnotationExportFormat.COCO:
                self._export_to_coco(db, images, temp_export_path, include_images)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            # 压缩文件夹
            zip_base_name = export_base_dir / f"{dataset.name.replace(' ', '_')}_{export_format.value}_annotations"
            archive_path = shutil.make_archive(
                base_name=str(zip_base_name),
                format='zip',
                root_dir=str(temp_export_path)
            )
            print(f"Annotations exported to {archive_path}")
            return archive_path
        finally:
            # 清理临时文件夹
            if temp_export_path.exists():
                shutil.rmtree(temp_export_path)
                print(f"Cleaned up temporary export folder: {temp_export_path}")

    def _get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """从图片文件获取尺寸"""
        try:
            with PILImage.open(image_path) as img:
                return img.width, img.height
        except Exception as e:
            raise ValueError(f"Error getting image dimensions for {image_path}: {e}")

    def _export_to_yolo(self, db: Session, images: List[models.Image], export_path: Path, include_images: bool):
        """导出为 YOLO 格式 (支持 YOLOv8 分割)"""
        labels_dir = export_path / "labels"
        labels_dir.mkdir()
        images_dir = export_path / "images"
        if include_images:
            images_dir.mkdir()

        # 预先收集所有标签并分配ID，确保 classes.txt 完整且有序
        all_labels = set()
        for img_record in images:
            annotations = crud_annotation.get_annotations_by_image(db, image_id=img_record.id)
            for ann in annotations:
                all_labels.add(ann.label)

        for label in sorted(list(all_labels)):  # 排序确保每次导出的ID一致
            self._get_class_id(label)

        # 写入 classes.txt
        classes_file_path = export_path / "classes.txt"
        with open(classes_file_path, 'w', encoding='utf-8') as f:
            for label, class_id in sorted(self.label_to_id_map.items(), key=lambda item: item[1]):
                f.write(f"{label}\n")

        for img_record in images:
            img_path_abs = Path(img_record.file_path)
            if not img_path_abs.exists():
                print(f"Warning: Image file not found at {img_path_abs}. Skipping image {img_record.filename}.")
                continue

            try:
                img_width, img_height = self._get_image_dimensions(img_path_abs)
            except ValueError as e:
                print(f"Warning: {e}. Skipping image {img_record.filename}.")
                continue

            annotations = crud_annotation.get_annotations_by_image(db, image_id=img_record.id)
            label_lines = []

            for ann in annotations:
                class_id = self._get_class_id(ann.label)

                if ann.annotation_type == models.AnnotationType.bbox:
                    coords = ann.coordinates
                    # YOLO 格式: class_id x_center y_center width height (归一化)
                    x_center = (coords['x'] + coords['width'] / 2) / img_width
                    y_center = (coords['y'] + coords['height'] / 2) / img_height
                    bbox_width = coords['width'] / img_width
                    bbox_height = coords['height'] / img_height
                    label_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}")

                elif ann.annotation_type == models.AnnotationType.polygon:
                    points = ann.coordinates['points']
                    if not points: continue
                    # YOLOv8 分割格式: class_id x1 y1 x2 y2 ... (归一化多边形点)
                    normalized_points = []
                    for p_x, p_y in points:
                        normalized_points.append(f"{p_x / img_width:.6f}")
                        normalized_points.append(f"{p_y / img_height:.6f}")
                    label_lines.append(f"{class_id} " + " ".join(normalized_points))

                elif ann.annotation_type == models.AnnotationType.point:
                    # 点标注在 YOLO 中通常不直接支持，这里转换为一个微小的边界框
                    coords = ann.coordinates
                    # 归一化中心点
                    x_center = coords['x'] / img_width
                    y_center = coords['y'] / img_height
                    # 给一个非常小的默认尺寸 (例如 5x5 像素)
                    bbox_width = 5 / img_width
                    bbox_height = 5 / img_height
                    label_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}")

            if label_lines:  # 只有当有标注时才创建文件
                label_file_path = labels_dir / f"{img_record.filename.split('.')[0]}.txt"
                with open(label_file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(label_lines))

            if include_images:
                shutil.copy(img_path_abs, images_dir / img_record.filename)

    def _export_to_pascal_voc(self, db: Session, images: List[models.Image], export_path: Path, include_images: bool):
        """导出为 Pascal VOC 格式"""
        annotations_dir = export_path / "Annotations"
        annotations_dir.mkdir()
        images_dir = export_path / "JPEGImages"
        if include_images:
            images_dir.mkdir()

        for img_record in images:
            img_path_abs = Path(img_record.file_path)
            if not img_path_abs.exists():
                print(f"Warning: Image file not found at {img_path_abs}. Skipping image {img_record.filename}.")
                continue

            try:
                img_width, img_height = self._get_image_dimensions(img_path_abs)
            except ValueError as e:
                print(f"Warning: {e}. Skipping image {img_record.filename}.")
                continue

            annotations = crud_annotation.get_annotations_by_image(db, image_id=img_record.id)

            # 创建 XML 根元素
            annotation_root = ET.Element("annotation")

            ET.SubElement(annotation_root, "folder").text = "JPEGImages"  # 默认文件夹名
            ET.SubElement(annotation_root, "filename").text = img_record.filename
            ET.SubElement(annotation_root, "path").text = str(img_path_abs)  # 原始绝对路径

            source = ET.SubElement(annotation_root, "source")
            ET.SubElement(source, "database").text = "Unknown"

            size = ET.SubElement(annotation_root, "size")
            ET.SubElement(size, "width").text = str(img_width)
            ET.SubElement(size, "height").text = str(img_height)
            ET.SubElement(size, "depth").text = "3"  # 假设是彩色图

            ET.SubElement(annotation_root, "segmented").text = "0"  # 0表示未分割

            for ann in annotations:
                obj = ET.SubElement(annotation_root, "object")
                ET.SubElement(obj, "name").text = ann.label
                ET.SubElement(obj, "pose").text = "Unspecified"
                ET.SubElement(obj, "truncated").text = "0"
                ET.SubElement(obj, "difficult").text = "0"

                bbox_elem = ET.SubElement(obj, "bndbox")
                if ann.annotation_type == models.AnnotationType.bbox:
                    coords = ann.coordinates
                    ET.SubElement(bbox_elem, "xmin").text = str(int(coords['x']))
                    ET.SubElement(bbox_elem, "ymin").text = str(int(coords['y']))
                    ET.SubElement(bbox_elem, "xmax").text = str(int(coords['x'] + coords['width']))
                    ET.SubElement(bbox_elem, "ymax").text = str(int(coords['y'] + coords['height']))
                elif ann.annotation_type == models.AnnotationType.polygon:
                    # 将多边形转换为其边界框 (Pascal VOC 不直接支持多边形分割)
                    points = ann.coordinates['points']
                    if not points: continue
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    xmin, ymin = min(xs), min(ys)
                    xmax, ymax = max(xs), max(ys)
                    ET.SubElement(bbox_elem, "xmin").text = str(int(xmin))
                    ET.SubElement(bbox_elem, "ymin").text = str(int(ymin))
                    ET.SubElement(bbox_elem, "xmax").text = str(int(xmax))
                    ET.SubElement(bbox_elem, "ymax").text = str(int(ymax))
                elif ann.annotation_type == models.AnnotationType.point:
                    # 将点转换为一个微小边界框 (例如 5x5 像素)
                    coords = ann.coordinates
                    ET.SubElement(bbox_elem, "xmin").text = str(int(coords['x'] - 2))
                    ET.SubElement(bbox_elem, "ymin").text = str(int(coords['y'] - 2))
                    ET.SubElement(bbox_elem, "xmax").text = str(int(coords['x'] + 2))
                    ET.SubElement(bbox_elem, "ymax").text = str(int(coords['y'] + 2))

            # 写入 XML 文件
            tree = ET.ElementTree(annotation_root)
            xml_file_path = annotations_dir / f"{img_record.filename.split('.')[0]}.xml"
            tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

            if include_images:
                shutil.copy(img_path_abs, images_dir / img_record.filename)

    def _export_to_coco(self, db: Session, images: List[models.Image], export_path: Path, include_images: bool):
        """导出为 COCO 格式"""
        coco_json_data: Dict[str, Any] = {
            "info": {
                "description": "Exported from Defect Detection System",
                "version": "1.0",
                "date_created": time.strftime("%Y/%m/%d")
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": []
        }

        images_dir = export_path / "images"
        if include_images:
            images_dir.mkdir()

        annotation_id_counter = 1
        image_id_counter = 1

        # 预先收集所有类别，确保 categories 列表完整且有序
        all_labels = set()
        for img_record in images:
            annotations = crud_annotation.get_annotations_by_image(db, image_id=img_record.id)
            for ann in annotations:
                all_labels.add(ann.label)

        for label in sorted(list(all_labels)):  # 排序确保每次导出的ID一致
            self._get_class_id(label)

        # 添加 categories
        for label, cat_id in sorted(self.label_to_id_map.items(), key=lambda item: item[1]):
            coco_json_data["categories"].append({
                "id": cat_id,
                "name": label,
                "supercategory": "defect"  # 默认设置为 "defect"
            })

        for img_record in images:
            img_path_abs = Path(img_record.file_path)
            if not img_path_abs.exists():
                print(f"Warning: Image file not found at {img_path_abs}. Skipping image {img_record.filename}.")
                continue

            try:
                img_width, img_height = self._get_image_dimensions(img_path_abs)
            except ValueError as e:
                print(f"Warning: {e}. Skipping image {img_record.filename}.")
                continue

            # 添加 image 信息
            coco_json_data["images"].append({
                "id": image_id_counter,
                "width": img_width,
                "height": img_height,
                "file_name": img_record.filename,
                "license": 0,  # 默认无许可证
                "flickr_url": "",
                "coco_url": ""
            })

            annotations = crud_annotation.get_annotations_by_image(db, image_id=img_record.id)
            for ann in annotations:
                category_id = self._get_class_id(ann.label)
                bbox = []  # [xmin, ymin, width, height]
                segmentation = []  # [[x1,y1,x2,y2,...]]

                if ann.annotation_type == models.AnnotationType.bbox:
                    coords = ann.coordinates
                    bbox = [coords['x'], coords['y'], coords['width'], coords['height']]
                    # COCO 的 segmentation 对于 bbox 而言，通常是 [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax, xmin, ymin]
                    # 注意：COCO 官方推荐的 bbox segmentation 是一个闭合的多边形
                    segmentation = [[
                        coords['x'], coords['y'],
                        coords['x'] + coords['width'], coords['y'],
                        coords['x'] + coords['width'], coords['y'] + coords['height'],
                        coords['x'], coords['y'] + coords['height'],
                        coords['x'], coords['y']  # 闭合
                    ]]
                elif ann.annotation_type == models.AnnotationType.polygon:
                    points = ann.coordinates['points']
                    if not points: continue
                    # COCO segmentation 是扁平化列表 [x1,y1,x2,y2,...]
                    # 确保多边形闭合
                    closed_points = points + [points[0]] if points[0] != points[-1] else points
                    segmentation = [[coord for p in closed_points for coord in p]]
                    # 计算多边形的边界框
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    xmin, ymin = min(xs), min(ys)
                    xmax, ymax = max(xs), max(ys)
                    bbox = [xmin, ymin, xmax - xmin, ymax - ymin]
                elif ann.annotation_type == models.AnnotationType.point:
                    # 将点转换为一个微小边界框和对应的分割
                    coords = ann.coordinates
                    xmin, ymin = coords['x'] - 2, coords['y'] - 2  # 2像素半径
                    xmax, ymax = coords['x'] + 2, coords['y'] + 2
                    bbox = [xmin, ymin, xmax - xmin, ymax - ymin]
                    segmentation = [[
                        xmin, ymin,
                        xmax, ymin,
                        xmax, ymax,
                        xmin, ymax,
                        xmin, ymin  # 闭合
                    ]]

                if bbox:  # 只有当有有效坐标时才添加标注
                    coco_json_data["annotations"].append({
                        "id": annotation_id_counter,
                        "image_id": image_id_counter,
                        "category_id": category_id,
                        "bbox": [round(float(x), 2) for x in bbox],  # 浮点数保留两位小数
                        "area": round(float(bbox[2] * bbox[3]), 2),  # 面积
                        "segmentation": [[round(float(coord), 2) for coord in seg_list] for seg_list in segmentation],
                        "iscrowd": 0  # 0表示非重叠
                    })
                    annotation_id_counter += 1

            if include_images:
                shutil.copy(img_path_abs, images_dir / img_record.filename)

            image_id_counter += 1

        # 写入 COCO JSON 文件
        coco_json_path = export_path / "annotations.json"
        with open(coco_json_path, 'w', encoding='utf-8') as f:
            json.dump(coco_json_data, f, indent=4, ensure_ascii=False)


annotation_exporter = AnnotationExporter()