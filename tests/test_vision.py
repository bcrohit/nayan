"""Vision service tests."""

import json

import pytest

from app.vision import parse_json_response


def test_parse_json_response_plain() -> None:
    payload = {"action": "STOP", "speech_text": "Stop now."}
    assert parse_json_response(json.dumps(payload)) == payload


def test_parse_json_response_markdown_wrapped() -> None:
    raw = '```json\n{"action": "CONTINUE", "speech_text": "Path is clear."}\n```'
    assert parse_json_response(raw)["action"] == "CONTINUE"


def test_parse_json_response_invalid() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_json_response("not json")
