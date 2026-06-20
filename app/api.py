"""HTTP routes for the camera snapshot proxy."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.camera_client import CameraClient, InvalidSnapshotError

router = APIRouter()


def _camera(request: Request) -> CameraClient:
    return request.app.state.camera


@router.get("/snapshot")
async def snapshot(request: Request) -> Response:
    camera = _camera(request)

    try:
        frame_bytes = await camera.get_snapshot()
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

    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/health")
async def health(request: Request) -> dict[str, bool | str]:
    camera = _camera(request)
    return {
        "status": "ok",
        "camera_connected": await camera.is_connected(),
    }
