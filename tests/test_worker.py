"""Tests for the capture worker."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.buffer.frame_buffer import FrameBuffer
from app.camera.client import CameraClient, CameraConnectionError
from app.camera.worker import FrameCaptureWorker


@pytest.fixture
def camera() -> CameraClient:
    return CameraClient(
        "http://camera.local",
        connection_timeout_seconds=1.0,
        read_timeout_seconds=1.0,
        max_retries=1,
        retry_base_delay_seconds=0.01,
        max_connections=2,
        max_keepalive_connections=1,
    )


@pytest.mark.asyncio
async def test_worker_captures_and_buffers(camera: CameraClient, monkeypatch: pytest.MonkeyPatch) -> None:
    frame_buffer = FrameBuffer(max_size=2)
    capture_mock = AsyncMock(side_effect=[b"\xff\xd8\xff\xd9", b"\xff\xd8\xff\xd8"])
    monkeypatch.setattr(camera, "capture_frame", capture_mock)
    connect_mock = AsyncMock()
    monkeypatch.setattr(camera, "connect", connect_mock)

    worker = FrameCaptureWorker(
        camera,
        frame_buffer,
        interval_seconds=0.01,
        success_log_interval=100,
        error_backoff_seconds=0.01,
    )

    await worker.start()
    await asyncio.sleep(0.05)
    await worker.stop()

    assert capture_mock.await_count >= 1
    assert frame_buffer.get_latest() == b"\xff\xd8\xff\xd8"
    assert worker.last_capture_at is not None


@pytest.mark.asyncio
async def test_worker_recovers_from_camera_errors(
    camera: CameraClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame_buffer = FrameBuffer(max_size=2)
    capture_mock = AsyncMock(
        side_effect=[
            CameraConnectionError("offline"),
            b"\xff\xd8\xff\xd9",
        ]
    )
    monkeypatch.setattr(camera, "capture_frame", capture_mock)
    monkeypatch.setattr(camera, "connect", AsyncMock())

    worker = FrameCaptureWorker(
        camera,
        frame_buffer,
        interval_seconds=0.01,
        success_log_interval=100,
        error_backoff_seconds=0.01,
    )

    await worker.start()
    await asyncio.sleep(0.08)
    await worker.stop()

    assert capture_mock.await_count >= 2
    assert frame_buffer.get_latest() == b"\xff\xd8\xff\xd9"
