"""Async HTTP client for IP Webcam image capture."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Final

import httpx

logger = logging.getLogger(__name__)

_JPEG_MAGIC: Final[bytes] = b"\xff\xd8\xff"
_PHOTO_PATH: Final[str] = "/photo.jpg"


class CameraError(Exception):
    """Base class for camera-related failures."""


class CameraConnectionError(CameraError):
    """Raised when the camera cannot be reached."""


class CameraTimeoutError(CameraError):
    """Raised when a camera request times out."""


class InvalidImageResponseError(CameraError):
    """Raised when the camera response is not a valid JPEG payload."""


class CameraClient:
    """High-performance async client for IP Webcam snapshot capture."""

    def __init__(
        self,
        camera_url: str,
        *,
        connection_timeout_seconds: float,
        read_timeout_seconds: float,
        max_retries: int,
        retry_base_delay_seconds: float,
        max_connections: int,
        max_keepalive_connections: int,
    ) -> None:
        self._base_url = camera_url.rstrip("/")
        self._photo_url = f"{self._base_url}{_PHOTO_PATH}"
        self._connection_timeout_seconds = connection_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._max_retries = max_retries
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    @property
    def camera_url(self) -> str:
        return self._base_url

    @property
    def photo_url(self) -> str:
        return self._photo_url

    async def connect(self) -> None:
        """Create or reuse the shared async HTTP client."""
        async with self._client_lock:
            if self._client is not None:
                return

            timeout = httpx.Timeout(
                connect=self._connection_timeout_seconds,
                read=self._read_timeout_seconds,
                write=self._read_timeout_seconds,
                pool=self._connection_timeout_seconds,
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=self._limits,
                follow_redirects=True,
            )

    async def close(self) -> None:
        """Close the underlying HTTP client and release pooled connections."""
        async with self._client_lock:
            if self._client is None:
                return

            await self._client.aclose()
            self._client = None

    async def update_camera_url(self, camera_url: str) -> None:
        """Point the client at a different camera base URL."""
        self._base_url = camera_url.rstrip("/")
        self._photo_url = f"{self._base_url}{_PHOTO_PATH}"

    async def probe_connectivity(self) -> bool:
        """Perform a single lightweight connectivity check without retries."""
        await self.connect()
        assert self._client is not None

        try:
            response = await self._client.get(self._photo_url)
            if response.status_code != httpx.codes.OK:
                return False

            self._validate_jpeg(response.content)
            return True
        except (httpx.HTTPError, InvalidImageResponseError):
            return False

    async def health_check(self) -> bool:
        """Return True when the camera responds with a valid JPEG snapshot."""
        return await self.probe_connectivity()

    async def capture_frame(self) -> bytes:
        """Fetch a single JPEG snapshot and return the raw response bytes."""
        await self.connect()
        assert self._client is not None

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            started = time.perf_counter()
            try:
                response = await self._client.get(self._photo_url)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)

                if response.status_code != httpx.codes.OK:
                    raise InvalidImageResponseError(
                        f"Unexpected status code {response.status_code} from camera"
                    )

                frame_bytes = response.content
                self._validate_jpeg(frame_bytes)

                logger.debug(
                    "Camera frame captured",
                    extra={
                        "event": "capture_success",
                        "latency_ms": latency_ms,
                        "camera_url": self._base_url,
                        "attempt": attempt,
                    },
                )
                return frame_bytes

            except httpx.TimeoutException as exc:
                last_error = CameraTimeoutError("Camera request timed out")
                last_error.__cause__ = exc
            except httpx.RequestError as exc:
                last_error = CameraConnectionError(f"Camera network failure: {exc}")
                last_error.__cause__ = exc
            except InvalidImageResponseError as exc:
                last_error = exc
            except CameraError as exc:
                last_error = exc

            if attempt < self._max_retries:
                delay = self._retry_base_delay_seconds * attempt
                logger.warning(
                    "Capture attempt failed; retrying",
                    extra={
                        "event": "capture_retry",
                        "camera_url": self._base_url,
                        "attempt": attempt,
                        "error_type": type(last_error).__name__ if last_error else "Unknown",
                    },
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        logger.error(
            "Capture failed after retries",
            extra={
                "event": "capture_failure",
                "camera_url": self._base_url,
                "attempt": self._max_retries,
                "error_type": type(last_error).__name__,
            },
        )
        raise last_error

    @staticmethod
    def _validate_jpeg(frame_bytes: bytes) -> None:
        if not frame_bytes:
            raise InvalidImageResponseError("Camera returned an empty response body")

        if not frame_bytes.startswith(_JPEG_MAGIC):
            raise InvalidImageResponseError("Camera response is not a JPEG image")

        content_type_hint = frame_bytes[:32].lower()
        if b"<html" in content_type_hint or b"<!doctype html" in content_type_hint:
            raise InvalidImageResponseError("Camera returned HTML instead of JPEG bytes")
