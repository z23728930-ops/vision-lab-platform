# app/ml_models/faster_rcnn_model.py

import torchvision
from torchvision.models.detection.faster_rcnn import FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.rpn import AnchorGenerator # 尽管在get_faster_rcnn_model中未使用，但保留以防将来扩展

def get_faster_rcnn_model(num_classes=2, pretrained=True):
    """
    获取 Faster R-CNN 模型。
    Args:
        num_classes (int): 类别数量，包括背景。例如，如果有一个缺陷类别，则 num_classes=2 (背景+缺陷)。
        pretrained (bool): 是否使用预训练权重。
    Returns:
        torchvision.models.detection.FasterRCNN: Faster R-CNN 模型实例。
    """
    if pretrained:
        # 使用默认的预训练权重
        weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)
    else:
        # 不使用预训练权重
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)

    # 获取分类器的输入特征数量
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    # 替换预训练模型的头部，使其适应新的类别数量
    model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(in_features, num_classes)

    return model