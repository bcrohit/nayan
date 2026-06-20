"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.logging_config import configure_logging
from app.services import CapturePipeline


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    pipeline = CapturePipeline.from_settings(settings)
    app.state.pipeline = pipeline

    try:
        yield
    finally:
        await pipeline.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Nayan Capture Service",
        description="High-performance image acquisition pipeline for IP Webcam.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"service": "nayan-capture", "docs": "/docs"}

    return app


app = create_app()
