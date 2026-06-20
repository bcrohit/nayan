"""Minimal async HTTP client for IP camera snapshot fetching."""

from __future__ import annotations

import httpx

_JPEG_MAGIC = b"\xff\xd8\xff"


class InvalidSnapshotError(Exception):
    """Raised when the camera response is not a valid JPEG snapshot."""


class CameraClient:
    """Reuses a single httpx.AsyncClient for low-latency snapshot fetches."""

    def __init__(self, camera_url: str, timeout_seconds: float) -> None:
        self._camera_url = camera_url
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                follow_redirects=True,
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_snapshot(self) -> bytes:
        """Fetch one JPEG snapshot and return raw bytes."""
        client = self._client
        if client is None:
            raise RuntimeError("CameraClient has not been started")

        response = await client.get(self._camera_url)
        if response.status_code != httpx.codes.OK:
            raise InvalidSnapshotError(f"Camera returned status {response.status_code}")

        frame_bytes = response.content
        if not frame_bytes.startswith(_JPEG_MAGIC):
            raise InvalidSnapshotError("Camera response is not a JPEG image")

        return frame_bytes

    async def is_connected(self) -> bool:
        """Lightweight connectivity probe against the camera snapshot endpoint."""
        client = self._client
        if client is None:
            return False

        try:
            response = await client.get(self._camera_url)
            return (
                response.status_code == httpx.codes.OK
                and response.content[:3] == _JPEG_MAGIC
            )
        except httpx.HTTPError:
            return False
