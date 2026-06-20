"""Background worker that periodically captures frames from the camera."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

from app.buffer.frame_buffer import FrameBuffer
from app.camera.client import CameraClient, CameraError

logger = logging.getLogger(__name__)


class FrameCaptureWorker:
    """Continuous async capture loop that feeds a frame buffer."""

    def __init__(
        self,
        camera: CameraClient,
        frame_buffer: FrameBuffer,
        *,
        interval_seconds: float,
        success_log_interval: int,
        error_backoff_seconds: float,
    ) -> None:
        self._camera = camera
        self._frame_buffer = frame_buffer
        self._interval_seconds = interval_seconds
        self._success_log_interval = success_log_interval
        self._error_backoff_seconds = error_backoff_seconds

        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._interval_lock = asyncio.Lock()
        self._last_capture_at: datetime | None = None
        self._successful_capture_count = 0

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def interval_seconds(self) -> float:
        return self._interval_seconds

    @property
    def last_capture_at(self) -> datetime | None:
        return self._last_capture_at

    async def set_interval_seconds(self, interval_seconds: float) -> None:
        """Update the capture interval for the running worker."""
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")

        async with self._interval_lock:
            self._interval_seconds = interval_seconds

    async def start(self) -> None:
        """Start the background capture loop."""
        if self.is_running:
            return

        self._stop_event.clear()
        await self._camera.connect()
        self._task = asyncio.create_task(self._run(), name="frame-capture-worker")

    async def stop(self) -> None:
        """Stop the background capture loop and wait for graceful shutdown."""
        if not self.is_running:
            return

        self._stop_event.set()
        assert self._task is not None
        await self._task
        self._task = None

    async def _run(self) -> None:
        logger.info(
            "Capture worker started",
            extra={
                "event": "worker_started",
                "camera_url": self._camera.camera_url,
            },
        )

        try:
            while not self._stop_event.is_set():
                loop_started = time.perf_counter()

                try:
                    frame_bytes = await self._camera.capture_frame()
                    await self._frame_buffer.put(frame_bytes)

                    self._last_capture_at = datetime.now(tz=UTC)
                    self._successful_capture_count += 1

                    if self._successful_capture_count % self._success_log_interval == 0:
                        logger.info(
                            "Capture worker heartbeat",
                            extra={
                                "event": "capture_success",
                                "latency_ms": round((time.perf_counter() - loop_started) * 1000, 2),
                                "queue_size": self._frame_buffer.size(),
                                "camera_url": self._camera.camera_url,
                            },
                        )
                except CameraError as exc:
                    logger.warning(
                        "Capture worker recovered from camera error",
                        extra={
                            "event": "capture_failure",
                            "error_type": type(exc).__name__,
                            "camera_url": self._camera.camera_url,
                            "queue_size": self._frame_buffer.size(),
                        },
                    )
                    await self._sleep_with_stop(self._error_backoff_seconds)
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "Unexpected capture worker error",
                        extra={
                            "event": "capture_failure",
                            "error_type": type(exc).__name__,
                            "camera_url": self._camera.camera_url,
                        },
                    )
                    await self._sleep_with_stop(self._error_backoff_seconds)
                    continue

                elapsed = time.perf_counter() - loop_started
                async with self._interval_lock:
                    interval_seconds = self._interval_seconds
                sleep_seconds = max(0.0, interval_seconds - elapsed)
                await self._sleep_with_stop(sleep_seconds)
        finally:
            logger.info(
                "Capture worker stopped",
                extra={"event": "worker_stopped", "camera_url": self._camera.camera_url},
            )

    async def _sleep_with_stop(self, seconds: float) -> None:
        if seconds <= 0 or self._stop_event.is_set():
            return

        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except TimeoutError:
            return
