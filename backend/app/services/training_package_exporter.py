import json
import shutil
import tempfile
from pathlib import Path

from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.db import models


def create_yolo_training_package(db: Session, dataset: models.Dataset, manifest: dict, output_root: Path, experience: bool = False) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix=f"training_{dataset.id}_", dir=str(output_root)))
    suffix = "YOLO_experience_training" if experience else "YOLO_training"
    package_dir = work_dir / f"{dataset.name.replace(' ', '_')}_{suffix}"
    package_dir.mkdir()
    class_names = sorted({ann.label for image in dataset.images for ann in image.annotations})
    if not class_names:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise ValueError("数据集中没有任何缺陷标注，无法生成YOLO训练包。")
    class_ids = {name: index for index, name in enumerate(class_names)}
    images_by_id = {image.id: image for image in dataset.images}

    for split_name in ("train", "val", "test"):
        image_dir = package_dir / "images" / split_name
        label_dir = package_dir / "labels" / split_name
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        for item in manifest.get("splits", {}).get(split_name, []):
            image = images_by_id.get(int(item["id"]))
            if not image or not Path(image.file_path).exists():
                continue
            output_name = f"{image.id}_{image.filename}"
            shutil.copy2(image.file_path, image_dir / output_name)
            with PILImage.open(image.file_path) as source_image:
                width, height = source_image.size
            lines = []
            for annotation in image.annotations:
                class_id = class_ids[annotation.label]
                coords = annotation.coordinates
                if annotation.annotation_type == models.AnnotationType.bbox:
                    x_center = (coords["x"] + coords["width"] / 2) / width
                    y_center = (coords["y"] + coords["height"] / 2) / height
                    lines.append(f'{class_id} {x_center:.6f} {y_center:.6f} {coords["width"] / width:.6f} {coords["height"] / height:.6f}')
                elif annotation.annotation_type == models.AnnotationType.polygon:
                    points = " ".join(f"{x / width:.6f} {y / height:.6f}" for x, y in coords.get("points", []))
                    if points:
                        lines.append(f"{class_id} {points}")
            (label_dir / f"{Path(output_name).stem}.txt").write_text("\n".join(lines), encoding="utf-8")

    yaml_lines = ["train: images/train", "val: images/val", "test: images/test", "names:"]
    yaml_lines.extend(f"  {index}: {json.dumps(name, ensure_ascii=False)}" for index, name in enumerate(class_names))
    (package_dir / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    (package_dir / "split_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "requirements.txt").write_text("ultralytics>=8.3,<9\n", encoding="utf-8")
    epochs = 10 if experience else 50
    run_name = "experience_training" if experience else "group_training"
    (package_dir / "train.py").write_text(
        'from ultralytics import YOLO\n\n'
        'MODEL = "yolo11n.pt"\n'
        'model = YOLO(MODEL)\n'
        f'model.train(data="data.yaml", epochs={epochs}, imgsz=640, batch=2, project="runs/detect", name="{run_name}", seed=42)\n'
        'model.val(data="data.yaml", split="test")\n'
        f'print("训练完成，模型位于 runs/detect/{run_name}/weights/best.pt")\n',
        encoding="utf-8",
    )
    warning = "【重要】这是少量样本体验训练，模型仅用于观察训练流程，不用于正式质检或性能评价。\n" if experience else ""
    (package_dir / "训练说明.txt").write_text(
        warning +
        "1. 在本目录打开PowerShell。\n"
        "2. 执行：python -m pip install -r requirements.txt\n"
        "3. 执行：python train.py\n"
        "4. 第一次运行会下载yolo11n.pt；无网络时请由教师提前放入本目录。\n"
        f"5. 训练完成后模型位于 runs/detect/{run_name}/weights/best.pt。\n"
        "6. 各组只修改教师指定的训练变量，其余参数保持一致。\n",
        encoding="utf-8",
    )
    archive_kind = "experience_training_package" if experience else "training_package"
    archive_base = output_root / f"{archive_kind}_{dataset.id}_{work_dir.name}"
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=package_dir))
    shutil.rmtree(work_dir, ignore_errors=True)
    return archive_path
