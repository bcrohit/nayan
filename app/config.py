"""Application configuration from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    camera_url: str = Field(
        default="http://192.168.103.180:8080/photo.jpg",
        validation_alias="CAMERA_URL",
    )
    timeout_seconds: float = Field(default=3.0, validation_alias="TIMEOUT_SECONDS", gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
