"""API tests."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.camera_client import CameraClient, InvalidSnapshotError
from app.main import app
from app.tts import TTSService
from app.vision import VisionService


@pytest.fixture
def client() -> TestClient:
    camera = CameraClient("http://camera.local/photo.jpg", timeout_seconds=1.0)
    vision = MagicMock(spec=VisionService)
    vision.is_configured = True
    vision.describe = AsyncMock(
        return_value={"action": "CONTINUE", "speech_text": "Path is clear."}
    )

    tts = MagicMock(spec=TTSService)
    tts.is_ready = True
    tts.is_running = True
    tts.speak = MagicMock()

    with TestClient(app) as test_client:
        app.state.camera = camera
        app.state.vision = vision
        app.state.tts = tts
        yield test_client


def test_health_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.state.camera, "is_connected", AsyncMock(return_value=True))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "camera_connected": True,
        "vision_ready": True,
        "tts_ready": True,
    }


def test_snapshot_returns_jpeg(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    jpeg = b"\xff\xd8\xff\xd9"
    monkeypatch.setattr(app.state.camera, "get_snapshot", AsyncMock(return_value=jpeg))

    response = client.get("/snapshot")

    assert response.status_code == 200
    assert response.content == jpeg
    assert response.headers["content-type"] == "image/jpeg"


def test_describe_returns_guidance(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.state.camera, "get_snapshot", AsyncMock(return_value=b"\xff\xd8\xff\xd9"))

    response = client.get("/describe")

    assert response.status_code == 200
    assert response.json() == {"action": "CONTINUE", "speech_text": "Path is clear."}
    app.state.vision.describe.assert_awaited_once()


def test_navigate_with_speech(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    app.state.vision.describe = AsyncMock(
        return_value={"action": "TURN_LEFT", "speech_text": "Turn left now."}
    )
    monkeypatch.setattr(app.state.camera, "get_snapshot", AsyncMock(return_value=b"\xff\xd8\xff\xd9"))

    response = client.get("/navigate?speak=true")

    assert response.status_code == 200
    app.state.tts.speak.assert_called_once_with("Turn left now.", "TURN_LEFT")


def test_navigate_continue_skips_speech(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.state.camera, "get_snapshot", AsyncMock(return_value=b"\xff\xd8\xff\xd9"))

    response = client.get("/navigate?speak=true")

    assert response.status_code == 200
    assert response.json() == {"action": "CONTINUE", "speech_text": "Path is clear."}
    app.state.tts.speak.assert_not_called()


def test_speak_queues_request(client: TestClient) -> None:
    response = client.post("/speak", json={"text": "Stop.", "action": "STOP"})

    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    app.state.tts.speak.assert_called_once_with("Stop.", "STOP")


def test_snapshot_timeout(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.state.camera,
        "get_snapshot",
        AsyncMock(side_effect=httpx.TimeoutException("timed out")),
    )

    response = client.get("/snapshot")

    assert response.status_code == 504


def test_snapshot_unreachable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.state.camera,
        "get_snapshot",
        AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    )

    response = client.get("/snapshot")

    assert response.status_code == 502


def test_snapshot_invalid_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.state.camera,
        "get_snapshot",
        AsyncMock(side_effect=InvalidSnapshotError("Camera response is not a JPEG image")),
    )

    response = client.get("/snapshot")

    assert response.status_code == 502
