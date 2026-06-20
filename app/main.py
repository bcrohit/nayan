"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.camera_client import CameraClient
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    camera = CameraClient(settings.camera_url, settings.timeout_seconds)
    await camera.start()
    app.state.camera = camera
    try:
        yield
    finally:
        await camera.close()


app = FastAPI(
    title="Nayan Snapshot Proxy",
    description="On-demand IP camera snapshot fetching for downstream processing.",
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(router)
