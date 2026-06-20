"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the capture pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="NAYAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    camera_url: str = Field(
        default="http://localhost:8080",
        description="Base URL of the IP Webcam instance.",
    )
    capture_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Default interval between frame captures.",
    )
    queue_max_size: int = Field(
        default=8,
        ge=1,
        description="Maximum number of frames retained in the buffer.",
    )

    connection_timeout_seconds: float = Field(default=5.0, gt=0)
    read_timeout_seconds: float = Field(default=15.0, gt=0)
    capture_max_retries: int = Field(default=3, ge=1)
    capture_retry_base_delay_seconds: float = Field(default=0.25, gt=0)

    max_connections: int = Field(default=10, ge=1)
    max_keepalive_connections: int = Field(default=5, ge=1)

    log_level: str = Field(default="INFO")
    capture_success_log_interval: int = Field(
        default=30,
        ge=1,
        description="Log a capture success summary every N successful frames.",
    )
    worker_error_backoff_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Delay before retrying after a capture failure.",
    )


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
