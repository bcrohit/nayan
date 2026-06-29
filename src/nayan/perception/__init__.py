from __future__ import annotations

from nayan.perception.base import ObstacleDetector, WalkableRegionDetector
from nayan.perception.walkable_onnx import OnnxWalkableDetector

__all__ = [
    "ObstacleDetector",
    "WalkableRegionDetector",
    "OnnxWalkableDetector",
]


def create_walkable_detector(
    backend: str = "onnx",
    *,
    inference_size: int = 512,
    device: str | None = None,
) -> WalkableRegionDetector:
    if backend == "onnx":
        return OnnxWalkableDetector(inference_size=inference_size)

    if backend == "torch":
        from nayan.perception.walkable_torch import TorchWalkableDetector

        return TorchWalkableDetector(inference_width=inference_size, device=device)

    raise ValueError(f"Unknown walkable detector backend: {backend!r}. Use 'onnx' or 'torch'.")
