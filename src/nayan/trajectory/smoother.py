from __future__ import annotations

import numpy as np

from nayan.types import Trajectory


class TrajectorySmoother:
    """Temporal smoothing of trajectory centerline across frames."""

    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = alpha
        self._prev_center_x: np.ndarray | None = None

    def reset(self) -> None:
        self._prev_center_x = None

    def smooth(self, trajectory: Trajectory) -> Trajectory:
        centerline = trajectory.centerline.copy()
        left = trajectory.left_boundary.copy()
        right = trajectory.right_boundary.copy()

        center_x = centerline[:, 0].astype(np.float32)

        if self._prev_center_x is not None and len(self._prev_center_x) == len(center_x):
            center_x = self.alpha * center_x + (1.0 - self.alpha) * self._prev_center_x
            delta = center_x - centerline[:, 0]
            centerline[:, 0] = center_x.astype(np.int32)
            left[:, 0] = (left[:, 0] + delta).astype(np.int32)
            right[:, 0] = (right[:, 0] + delta).astype(np.int32)

        self._prev_center_x = center_x

        return Trajectory(
            centerline=centerline,
            left_boundary=left,
            right_boundary=right,
            vanishing_point=trajectory.vanishing_point,
        )
