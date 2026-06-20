"""Tests for the frame buffer."""

import asyncio

import pytest

from app.buffer.frame_buffer import FrameBuffer


@pytest.mark.asyncio
async def test_put_and_get_latest() -> None:
    buffer = FrameBuffer(max_size=2)

    await buffer.put(b"frame-1")
    await buffer.put(b"frame-2")

    assert buffer.get_latest() == b"frame-2"
    assert buffer.size() == 2


@pytest.mark.asyncio
async def test_drop_oldest_when_full() -> None:
    buffer = FrameBuffer(max_size=2)

    await buffer.put(b"frame-1")
    await buffer.put(b"frame-2")
    await buffer.put(b"frame-3")

    assert buffer.size() == 2
    assert buffer.get_latest() == b"frame-3"


@pytest.mark.asyncio
async def test_concurrent_puts() -> None:
    buffer = FrameBuffer(max_size=4)

    await asyncio.gather(*(buffer.put(f"frame-{index}".encode()) for index in range(20)))

    assert buffer.size() == 4
    assert buffer.get_latest() == b"frame-19"
