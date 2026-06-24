from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from nayan.types import WalkableRegion


class WalkableRegionDetector(ABC):
    """Detect walkable surfaces (sidewalk, road, floor) in an egocentric frame."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> WalkableRegion:
        """Return a binary walkable mask aligned with the input frame."""


class ObstacleDetector(ABC):
    """Future: detect obstacles intersecting the walking trajectory."""

    @abstractmethod
    def detect(self, frame: np.ndarray, walkable_mask: np.ndarray) -> list[dict]:
        """Return obstacle detections for downstream prioritization and LLM use."""
