"""Navigation polling client tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.run import poll_navigate, wait_for_api


@pytest.mark.asyncio
async def test_poll_navigate() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"action": "STOP", "speech_text": "Stop now."}
    client.get = AsyncMock(return_value=response)

    result = await poll_navigate(client, "http://localhost:8000")

    assert result == {"action": "STOP", "speech_text": "Stop now."}
    client.get.assert_awaited_once_with("http://localhost:8000/navigate?speak=true")


@pytest.mark.asyncio
async def test_wait_for_api_returns_when_healthy() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    response = MagicMock(status_code=200)
    client.get = AsyncMock(return_value=response)
    stop = asyncio.Event()

    ready = await wait_for_api(client, "http://localhost:8000", stop)

    assert ready is True
    client.get.assert_awaited_once_with("http://localhost:8000/health")
