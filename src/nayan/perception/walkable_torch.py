from __future__ import annotations

import numpy as np

from nayan.perception.base import WalkableRegionDetector
from nayan.perception.walkable_common import CITYSCAPES_WALKABLE, DEFAULT_TORCH_MODEL
from nayan.types import WalkableRegion


class TorchWalkableDetector(WalkableRegionDetector):
    """Semantic segmentation of walkable regions using SegFormer via PyTorch."""

    def __init__(
        self,
        model_name: str = DEFAULT_TORCH_MODEL,
        device: str | None = None,
        inference_width: int = 512,
    ) -> None:
        import torch
        from PIL import Image
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation

        self._torch = torch
        self._Image = Image
        self.inference_width = inference_width
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForSemanticSegmentation.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    def detect(self, frame: np.ndarray) -> WalkableRegion:
        torch = self._torch
        Image = self._Image

        height, width = frame.shape[:2]
        rgb = frame[:, :, ::-1]
        image = Image.fromarray(rgb)

        scale = self.inference_width / width
        infer_height = max(1, int(height * scale))
        resized = image.resize((self.inference_width, infer_height), Image.BILINEAR)

        inputs = self.processor(images=resized, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.inference_mode():
            logits = self.model(**inputs).logits

        upsampled = torch.nn.functional.interpolate(
            logits,
            size=(infer_height, self.inference_width),
            mode="bilinear",
            align_corners=False,
        )
        labels = upsampled.argmax(dim=1).squeeze(0).cpu().numpy()

        walkable_small = np.isin(labels, list(CITYSCAPES_WALKABLE)).astype(np.uint8) * 255
        walkable = np.array(
            Image.fromarray(walkable_small).resize((width, height), Image.NEAREST),
            dtype=np.uint8,
        )

        coverage = float(walkable.sum() / 255) / walkable.size
        return WalkableRegion(mask=walkable, confidence=coverage, source="segformer-torch-cityscapes")
