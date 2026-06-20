"""Bounded async frame buffer that prefers the latest image."""

from __future__ import annotations

import asyncio


class FrameBuffer:
    """Async bounded queue that drops the oldest frame when full."""

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")

        self._max_size = max_size
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=max_size)
        self._latest: bytes | None = None
        self._lock = asyncio.Lock()

    @property
    def max_size(self) -> int:
        return self._max_size

    async def put(self, frame_bytes: bytes) -> None:
        """Store a frame, evicting the oldest entry when the buffer is full."""
        async with self._lock:
            while self._queue.full():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            await self._queue.put(frame_bytes)
            self._latest = frame_bytes

    def get_latest(self) -> bytes | None:
        """Return the most recently captured frame without removing it."""
        return self._latest

    def size(self) -> int:
        """Return the current number of buffered frames."""
        return self._queue.qsize()

    def clear(self) -> None:
        """Remove all buffered frames."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._latest = None
