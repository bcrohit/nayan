"""API tests for the snapshot proxy."""

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.camera_client import CameraClient, InvalidSnapshotError
from app.main import app


@pytest.fixture
def client() -> TestClient:
    camera = CameraClient("http://camera.local/photo.jpg", timeout_seconds=1.0)
    app.state.camera = camera
    with TestClient(app) as test_client:
        yield test_client


def test_health_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.state.camera, "is_connected", AsyncMock(return_value=True))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "camera_connected": True}


def test_snapshot_returns_jpeg(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    jpeg = b"\xff\xd8\xff\xd9"
    monkeypatch.setattr(app.state.camera, "get_snapshot", AsyncMock(return_value=jpeg))

    response = client.get("/snapshot")

    assert response.status_code == 200
    assert response.content == jpeg
    assert response.headers["content-type"] == "image/jpeg"


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
