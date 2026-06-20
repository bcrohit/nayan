"""FastAPI route definitions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, HttpUrl

from app.services import CapturePipeline

router = APIRouter()


class CaptureStartRequest(BaseModel):
    camera_url: HttpUrl
    interval_seconds: float = Field(gt=0, description="Capture interval in seconds.")


class HealthResponse(BaseModel):
    status: str
    capture_running: bool
    camera_connected: bool
    queue_size: int
    last_capture_at: str | None


class CaptureControlResponse(BaseModel):
    status: str
    capture_running: bool
    camera_url: str
    interval_seconds: float


def get_pipeline(request: Request) -> CapturePipeline:
    return request.app.state.pipeline


PipelineDep = Annotated[CapturePipeline, Depends(get_pipeline)]


@router.get("/health", response_model=HealthResponse)
async def health(pipeline: PipelineDep) -> HealthResponse:
    camera_connected = await pipeline.camera.health_check()

    last_capture_at = pipeline.worker.last_capture_at
    return HealthResponse(
        status="ok",
        capture_running=pipeline.worker.is_running,
        camera_connected=camera_connected,
        queue_size=pipeline.frame_buffer.size(),
        last_capture_at=last_capture_at.isoformat() if last_capture_at else None,
    )


@router.post("/capture/start", response_model=CaptureControlResponse)
async def start_capture(body: CaptureStartRequest, pipeline: PipelineDep) -> CaptureControlResponse:
    async with pipeline.lifecycle_lock:
        camera_url = str(body.camera_url).rstrip("/")
        await pipeline.camera.update_camera_url(camera_url)
        await pipeline.worker.set_interval_seconds(body.interval_seconds)

        if pipeline.worker.is_running:
            return CaptureControlResponse(
                status="updated",
                capture_running=True,
                camera_url=pipeline.camera.camera_url,
                interval_seconds=pipeline.worker.interval_seconds,
            )

        await pipeline.worker.start()

    return CaptureControlResponse(
        status="started",
        capture_running=True,
        camera_url=pipeline.camera.camera_url,
        interval_seconds=pipeline.worker.interval_seconds,
    )


@router.post("/capture/stop", response_model=CaptureControlResponse)
async def stop_capture(pipeline: PipelineDep) -> CaptureControlResponse:
    async with pipeline.lifecycle_lock:
        if not pipeline.worker.is_running:
            return CaptureControlResponse(
                status="already_stopped",
                capture_running=False,
                camera_url=pipeline.camera.camera_url,
                interval_seconds=pipeline.worker.interval_seconds,
            )

        await pipeline.worker.stop()

    return CaptureControlResponse(
        status="stopped",
        capture_running=False,
        camera_url=pipeline.camera.camera_url,
        interval_seconds=pipeline.worker.interval_seconds,
    )


@router.get("/frame/latest")
async def latest_frame(pipeline: PipelineDep) -> Response:
    frame_bytes = pipeline.frame_buffer.get_latest()
    if frame_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No frame available yet",
        )

    return Response(content=frame_bytes, media_type="image/jpeg")
