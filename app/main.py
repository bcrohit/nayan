"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.camera_client import CameraClient
from app.config import get_settings
from app.tts import TTSService
from app.vision import VisionService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    camera = CameraClient(settings.camera_url, settings.timeout_seconds)
    await camera.start()

    vision = VisionService(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        prompt_file=settings.navigation_prompt_file,
        max_dimension=settings.image_max_dimension,
        rotate_degrees=settings.image_rotate_degrees,
    )

    tts = TTSService(
        voice=settings.tts_voice,
        rate=settings.tts_rate,
        cache_dir=settings.tts_cache_dir,
    )
    tts.start()

    app.state.camera = camera
    app.state.vision = vision
    app.state.tts = tts

    try:
        yield
    finally:
        tts.stop()
        await camera.close()


app = FastAPI(
    title="Nayan",
    description="Assistive navigation: camera snapshots, vision guidance, and speech output.",
    version="0.3.0",
    lifespan=lifespan,
)
app.include_router(router)
