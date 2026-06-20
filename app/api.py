"""HTTP routes for camera capture, vision, and speech."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.camera_client import CameraClient, InvalidSnapshotError
from app.tts import TTSService
from app.vision import VisionService, VisionServiceError

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    camera_connected: bool
    vision_ready: bool
    tts_ready: bool


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)
    action: str = Field(default="CONTINUE")


class NavigationResponse(BaseModel):
    action: str
    speech_text: str


def _camera(request: Request) -> CameraClient:
    return request.app.state.camera


def _vision(request: Request) -> VisionService:
    return request.app.state.vision


def _tts(request: Request) -> TTSService:
    return request.app.state.tts


async def _fetch_snapshot(camera: CameraClient) -> bytes:
    try:
        return await camera.get_snapshot()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Camera request timed out",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Camera unreachable",
        ) from exc
    except InvalidSnapshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    camera = _camera(request)
    vision = _vision(request)
    tts = _tts(request)

    return HealthResponse(
        status="ok",
        camera_connected=await camera.is_connected(),
        vision_ready=vision.is_configured,
        tts_ready=tts.is_ready and tts.is_running,
    )


@router.get("/snapshot")
async def snapshot(request: Request) -> Response:
    frame_bytes = await _fetch_snapshot(_camera(request))
    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/describe", response_model=NavigationResponse)
async def describe(request: Request) -> NavigationResponse:
    vision = _vision(request)
    if not vision.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vision service is not configured",
        )

    frame_bytes = await _fetch_snapshot(_camera(request))

    try:
        result = await vision.describe(frame_bytes)
    except VisionServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return NavigationResponse(
        action=str(result.get("action", "CONTINUE")),
        speech_text=str(result.get("speech_text", "")),
    )


@router.post("/speak")
async def speak(body: SpeakRequest, request: Request) -> dict[str, str]:
    tts = _tts(request)
    if not tts.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS dependencies are not installed",
        )

    tts.speak(body.text, body.action)
    return {"status": "queued"}


@router.get("/navigate", response_model=NavigationResponse)
async def navigate(
    request: Request,
    speak: bool = Query(default=False, description="Queue speech for the guidance text."),
) -> NavigationResponse:
    vision = _vision(request)
    if not vision.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vision service is not configured",
        )

    frame_bytes = await _fetch_snapshot(_camera(request))

    try:
        result = await vision.describe(frame_bytes)
    except VisionServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    guidance = NavigationResponse(
        action=str(result.get("action", "CONTINUE")),
        speech_text=str(result.get("speech_text", "")),
    )

    if speak and guidance.speech_text:
        tts = _tts(request)
        if tts.is_ready:
            tts.speak(guidance.speech_text, guidance.action)

    return guidance
