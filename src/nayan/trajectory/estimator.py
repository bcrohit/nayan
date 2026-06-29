from __future__ import annotations

import numpy as np

from nayan.types import Trajectory, WalkableRegion


class TrajectoryEstimator:
    """Extract a walking corridor centerline from a walkable-region mask."""

    def __init__(
        self,
        ground_start_ratio: float = 0.35,
        num_samples: int = 24,
        min_walkable_width_px: int = 20,
        boundary_inset_ratio: float = 0.15,
    ) -> None:
        self.ground_start_ratio = ground_start_ratio
        self.num_samples = num_samples
        self.min_walkable_width_px = min_walkable_width_px
        self.boundary_inset_ratio = boundary_inset_ratio

    def estimate(self, walkable: WalkableRegion, frame_shape: tuple[int, int]) -> Trajectory | None:
        height, width = frame_shape
        mask = walkable.mask
        y_start = int(height * self.ground_start_ratio)

        center_points: list[tuple[int, int]] = []
        left_points: list[tuple[int, int]] = []
        right_points: list[tuple[int, int]] = []

        sample_rows = np.linspace(height - 1, y_start, self.num_samples, dtype=int)

        for y in sample_rows:
            row = mask[y, :] > 0
            if not row.any():
                continue

            xs = np.flatnonzero(row)
            left_x = int(xs[0])
            right_x = int(xs[-1])
            corridor_width = right_x - left_x

            if corridor_width < self.min_walkable_width_px:
                continue

            inset = int(corridor_width * self.boundary_inset_ratio)
            left_x += inset
            right_x -= inset
            center_x = (left_x + right_x) // 2

            left_points.append((left_x, int(y)))
            right_points.append((right_x, int(y)))
            center_points.append((center_x, int(y)))

        if len(center_points) < 3:
            return None

        centerline = np.array(center_points, dtype=np.int32)
        left_boundary = np.array(left_points, dtype=np.int32)
        right_boundary = np.array(right_points, dtype=np.int32)

        vanishing_point = self._estimate_vanishing_point(centerline)

        return Trajectory(
            centerline=centerline,
            left_boundary=left_boundary,
            right_boundary=right_boundary,
            vanishing_point=vanishing_point,
        )

    @staticmethod
    def _estimate_vanishing_point(centerline: np.ndarray) -> tuple[int, int] | None:
        """Fit lines through upper and lower centerline segments; return their intersection."""
        if len(centerline) < 4:
            return None

        lower = centerline[: max(2, len(centerline) // 3)]
        upper = centerline[-max(2, len(centerline) // 3) :]

        lower_fit = np.polyfit(lower[:, 1], lower[:, 0], deg=1)
        upper_fit = np.polyfit(upper[:, 1], upper[:, 0], deg=1)

        # x = a*y + b  ->  a1*y + b1 = a2*y + b2
        a1, b1 = lower_fit
        a2, b2 = upper_fit

        if abs(a1 - a2) < 1e-6:
            return None

        y_vp = (b2 - b1) / (a1 - a2)
        x_vp = a1 * y_vp + b1

        if not np.isfinite(x_vp) or not np.isfinite(y_vp):
            return None

        return int(round(x_vp)), int(round(y_vp))
