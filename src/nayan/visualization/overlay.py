from __future__ import annotations

import cv2
import numpy as np

from nayan.types import Trajectory, WalkableRegion


class TrajectoryVisualizer:
    """Draw walkable mask and estimated walking corridor on a frame."""

    def __init__(
        self,
        show_walkable_mask: bool = True,
        mask_alpha: float = 0.25,
    ) -> None:
        self.show_walkable_mask = show_walkable_mask
        self.mask_alpha = mask_alpha

    def render(
        self,
        frame: np.ndarray,
        walkable: WalkableRegion | None = None,
        trajectory: Trajectory | None = None,
    ) -> np.ndarray:
        output = frame.copy()

        if self.show_walkable_mask and walkable is not None:
            output = self._overlay_mask(output, walkable.mask)

        if trajectory is not None:
            output = self._draw_polyline(output, trajectory.left_boundary, (0, 180, 255), 2)
            output = self._draw_polyline(output, trajectory.right_boundary, (0, 180, 255), 2)
            output = self._draw_polyline(output, trajectory.centerline, (0, 255, 120), 3)

            if trajectory.vanishing_point is not None:
                cv2.circle(output, trajectory.vanishing_point, 6, (255, 100, 0), -1)

        return output

    def _overlay_mask(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        overlay = frame.copy()
        overlay[mask > 0] = (40, 200, 40)
        return cv2.addWeighted(overlay, self.mask_alpha, frame, 1.0 - self.mask_alpha, 0)

    @staticmethod
    def _draw_polyline(
        frame: np.ndarray,
        points: np.ndarray,
        color: tuple[int, int, int],
        thickness: int,
    ) -> np.ndarray:
        if len(points) < 2:
            return frame

        pts = points.reshape(-1, 1, 2)
        cv2.polylines(frame, [pts], isClosed=False, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        return frame
