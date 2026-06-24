"""Smoke tests for trajectory geometry (no model weights required)."""

import numpy as np

from nayan.trajectory.estimator import TrajectoryEstimator
from nayan.trajectory.smoother import TrajectorySmoother
from nayan.types import WalkableRegion, Trajectory


def test_trajectory_from_synthetic_corridor() -> None:
    height, width = 480, 640
    mask = np.zeros((height, width), dtype=np.uint8)

    for y in range(int(height * 0.35), height):
        # Corridor narrows toward the top ( perspective ).
        progress = (y - height * 0.35) / (height * 0.65)
        half_width = int(80 + 120 * (1.0 - progress))
        cx = width // 2 + int(30 * (1.0 - progress))
        mask[y, max(0, cx - half_width) : min(width, cx + half_width)] = 255

    estimator = TrajectoryEstimator(num_samples=16)
    trajectory = estimator.estimate(WalkableRegion(mask=mask), (height, width))

    assert trajectory is not None
    assert len(trajectory.centerline) >= 3
    assert trajectory.centerline[0, 1] > trajectory.centerline[-1, 1]  # bottom to top


def test_smoother_reduces_jitter() -> None:
    base = np.array([[100, 400], [110, 350], [120, 300]], dtype=np.int32)
    jittered = Trajectory(
        centerline=base + np.array([[20, 0], [20, 0], [20, 0]]),
        left_boundary=base + np.array([[-40, 0], [-40, 0], [-40, 0]]),
        right_boundary=base + np.array([[40, 0], [40, 0], [40, 0]]),
    )

    smoother = TrajectorySmoother(alpha=0.5)
    smoother.smooth(jittered)
    second = smoother.smooth(
        Trajectory(
            centerline=base + np.array([[40, 0], [40, 0], [40, 0]]),
            left_boundary=base + np.array([[-40, 0], [-40, 0], [-40, 0]]),
            right_boundary=base + np.array([[40, 0], [40, 0], [40, 0]]),
        )
    )

    assert not np.array_equal(second.centerline[:, 0], (base + np.array([[40, 0], [40, 0], [40, 0]]))[:, 0])
