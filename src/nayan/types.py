from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class FrameContext:
    """Metadata for a single video frame."""

    index: int
    timestamp_sec: float
    width: int
    height: int


@dataclass
class WalkableRegion:
    """Binary mask and metadata for walkable surfaces in a frame."""

    mask: np.ndarray  # uint8, same HxW as source frame, 255 = walkable
    confidence: float = 1.0
    source: str = "segmentation"


@dataclass
class Trajectory:
    """Estimated walking path in image coordinates."""

    centerline: np.ndarray  # (N, 2) int32 [x, y]
    left_boundary: np.ndarray  # (N, 2) int32 [x, y]
    right_boundary: np.ndarray  # (N, 2) int32 [x, y]
    vanishing_point: tuple[int, int] | None = None


@dataclass
class PipelineResult:
    """Output of one pipeline step for a single frame."""

    frame: np.ndarray
    context: FrameContext
    walkable: WalkableRegion | None = None
    trajectory: Trajectory | None = None
    annotations: dict = field(default_factory=dict)
