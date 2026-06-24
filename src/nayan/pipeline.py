from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from nayan.perception.base import WalkableRegionDetector
from nayan.trajectory.estimator import TrajectoryEstimator
from nayan.trajectory.smoother import TrajectorySmoother
from nayan.types import FrameContext, PipelineResult
from nayan.video.io import VideoSource
from nayan.visualization.overlay import TrajectoryVisualizer


class TrajectoryPipeline:
    """Phase 1 pipeline: video in -> walkable mask -> trajectory -> visualization."""

    def __init__(
        self,
        walkable_detector: WalkableRegionDetector,
        trajectory_estimator: TrajectoryEstimator | None = None,
        smoother: TrajectorySmoother | None = None,
        visualizer: TrajectoryVisualizer | None = None,
    ) -> None:
        self.walkable_detector = walkable_detector
        self.trajectory_estimator = trajectory_estimator or TrajectoryEstimator()
        self.smoother = smoother or TrajectorySmoother()
        self.visualizer = visualizer or TrajectoryVisualizer()

    def process_frame(self, frame: np.ndarray, context: FrameContext) -> PipelineResult:
        walkable = self.walkable_detector.detect(frame)
        trajectory = self.trajectory_estimator.estimate(walkable, frame.shape[:2])

        if trajectory is not None:
            trajectory = self.smoother.smooth(trajectory)

        annotated = self.visualizer.render(frame, walkable=walkable, trajectory=trajectory)

        return PipelineResult(
            frame=annotated,
            context=context,
            walkable=walkable,
            trajectory=trajectory,
        )

    def run(self, source: VideoSource) -> Iterator[PipelineResult]:
        try:
            for index, timestamp, frame in source.frames():
                context = FrameContext(
                    index=index,
                    timestamp_sec=timestamp,
                    width=frame.shape[1],
                    height=frame.shape[0],
                )
                yield self.process_frame(frame, context)
        finally:
            source.close()

    def reset(self) -> None:
        self.smoother.reset()
