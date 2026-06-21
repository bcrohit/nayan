"""Application configuration from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    camera_url: str = Field(
        default="http://192.168.103.180:8080/photo.jpg",
        validation_alias="CAMERA_URL",
    )
    timeout_seconds: float = Field(default=3.0, validation_alias="TIMEOUT_SECONDS", gt=0)

    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="meta-llama/llama-4-scout-17b-16e-instruct",
        validation_alias="GROQ_MODEL",
    )
    navigation_prompt_file: str = Field(
        default="navigation.md",
        validation_alias="NAVIGATION_PROMPT_FILE",
    )
    image_max_dimension: int = Field(default=512, validation_alias="IMAGE_MAX_DIMENSION", ge=64)
    image_rotate_degrees: int = Field(default=90, validation_alias="IMAGE_ROTATE_DEGREES", ge=0)

    tts_voice: str = Field(default="en-US-JennyNeural", validation_alias="TTS_VOICE")
    tts_rate: float = Field(default=0.5, validation_alias="TTS_RATE", gt=0)
    tts_cache_dir: Path = Field(default=Path("/tmp/nayan_tts_cache"), validation_alias="TTS_CACHE_DIR")

    api_base_url: str = Field(default="http://127.0.0.1:8000", validation_alias="API_BASE_URL")
    poll_interval_seconds: float = Field(default=2.0, validation_alias="POLL_INTERVAL_SECONDS", gt=0)
    navigate_client_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="NAVIGATE_CLIENT_TIMEOUT_SECONDS",
        gt=0,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
