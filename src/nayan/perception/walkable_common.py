from __future__ import annotations

# Cityscapes semantic class IDs treated as walkable for Phase 1.
CITYSCAPES_WALKABLE = {0, 1}  # road, sidewalk

DEFAULT_ONNX_MODEL = "Xenova/segformer-b0-finetuned-cityscapes-512-1024"
DEFAULT_TORCH_MODEL = "nvidia/segformer-b0-finetuned-cityscapes-512-1024"

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
