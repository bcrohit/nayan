"""Capture pipeline service state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.buffer.frame_buffer import FrameBuffer
from app.camera.client import CameraClient
from app.camera.worker import FrameCaptureWorker
from app.config import Settings


@dataclass
class CapturePipeline:
    """Shared runtime objects for camera capture and buffering."""

    settings: Settings
    frame_buffer: FrameBuffer
    camera: CameraClient
    worker: FrameCaptureWorker
    lifecycle_lock: asyncio.Lock

    @classmethod
    def from_settings(cls, settings: Settings) -> CapturePipeline:
        frame_buffer = FrameBuffer(max_size=settings.queue_max_size)
        camera = CameraClient(
            settings.camera_url,
            connection_timeout_seconds=settings.connection_timeout_seconds,
            read_timeout_seconds=settings.read_timeout_seconds,
            max_retries=settings.capture_max_retries,
            retry_base_delay_seconds=settings.capture_retry_base_delay_seconds,
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_keepalive_connections,
        )
        worker = FrameCaptureWorker(
            camera,
            frame_buffer,
            interval_seconds=settings.capture_interval_seconds,
            success_log_interval=settings.capture_success_log_interval,
            error_backoff_seconds=settings.worker_error_backoff_seconds,
        )
        return cls(
            settings=settings,
            frame_buffer=frame_buffer,
            camera=camera,
            worker=worker,
            lifecycle_lock=asyncio.Lock(),
        )

    async def shutdown(self) -> None:
        """Stop background work and release camera connections."""
        async with self.lifecycle_lock:
            if self.worker.is_running:
                await self.worker.stop()
            await self.camera.close()
