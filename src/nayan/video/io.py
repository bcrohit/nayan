from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class VideoSource:
    """OpenCV-backed video or webcam source."""

    path: str | int
    max_frames: int | None = None

    def __post_init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> cv2.VideoCapture:
        if self._cap is not None and self._cap.isOpened():
            return self._cap

        self._cap = cv2.VideoCapture(self.path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video source: {self.path!r}")
        return self._cap

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def fps(self) -> float:
        assert self._cap is not None, "VideoSource not opened"
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0

    @property
    def width(self) -> int:
        assert self._cap is not None, "VideoSource not opened"
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        assert self._cap is not None, "VideoSource not opened"
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def frames(self) -> Iterator[tuple[int, float, np.ndarray]]:
        """Yield (frame_index, timestamp_sec, bgr_frame)."""
        if self._cap is None or not self._cap.isOpened():
            self.open()

        assert self._cap is not None
        fps = self.fps
        index = 0

        while True:
            if self.max_frames is not None and index >= self.max_frames:
                break

            ok, frame = self._cap.read()
            if not ok:
                break

            yield index, index / fps, frame
            index += 1


class VideoWriter:
    """Write annotated frames to a video file."""

    def __init__(self, path: str, fps: float, frame_size: tuple[int, int]) -> None:
        width, height = frame_size
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        if not self._writer.isOpened():
            raise RuntimeError(f"Could not open video writer: {path!r}")

    def write(self, frame: np.ndarray) -> None:
        self._writer.write(frame)

    def close(self) -> None:
        self._writer.release()
