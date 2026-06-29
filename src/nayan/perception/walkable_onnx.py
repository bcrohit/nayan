from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download

from nayan.perception.base import WalkableRegionDetector
from nayan.perception.walkable_common import CITYSCAPES_WALKABLE, DEFAULT_ONNX_MODEL
from nayan.types import WalkableRegion

_PROJECT_CACHE = Path(__file__).resolve().parents[3] / ".cache" / "huggingface"


class OnnxWalkableDetector(WalkableRegionDetector):
    """Walkable-region segmentation via ONNX SegFormer (no PyTorch required)."""

    def __init__(
        self,
        model_repo: str = DEFAULT_ONNX_MODEL,
        model_file: str = "onnx/model.onnx",
        inference_size: int = 512,
    ) -> None:
        self.model_repo = model_repo
        self.inference_size = inference_size

        model_path = hf_hub_download(
            repo_id=model_repo,
            filename=model_file,
            cache_dir=_PROJECT_CACHE,
        )
        config_path = hf_hub_download(
            repo_id=model_repo,
            filename="preprocessor_config.json",
            cache_dir=_PROJECT_CACHE,
        )

        with Path(config_path).open(encoding="utf-8") as handle:
            config = json.load(handle)

        self.mean = np.array(config.get("image_mean", [0.485, 0.456, 0.406]), dtype=np.float32)
        self.std = np.array(config.get("image_std", [0.229, 0.224, 0.225]), dtype=np.float32)
        self.rescale_factor = float(config.get("rescale_factor", 1 / 255))

        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            session_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            session_providers = ["CPUExecutionProvider"]

        self.session = ort.InferenceSession(model_path, providers=session_providers)
        self.input_name = self.session.get_inputs()[0].name

    def detect(self, frame: np.ndarray) -> WalkableRegion:
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        resized = cv2.resize(
            rgb,
            (self.inference_size, self.inference_size),
            interpolation=cv2.INTER_LINEAR,
        )
        tensor = resized.astype(np.float32) * self.rescale_factor
        tensor = (tensor - self.mean) / self.std
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...]

        outputs = self.session.run(None, {self.input_name: tensor})
        logits = outputs[0]
        labels = logits.argmax(axis=1).squeeze(0).astype(np.uint8)

        walkable_small = np.isin(labels, list(CITYSCAPES_WALKABLE)).astype(np.uint8) * 255
        walkable = cv2.resize(walkable_small, (width, height), interpolation=cv2.INTER_NEAREST)

        coverage = float(walkable.sum() / 255) / walkable.size
        return WalkableRegion(mask=walkable, confidence=coverage, source="segformer-onnx-cityscapes")
