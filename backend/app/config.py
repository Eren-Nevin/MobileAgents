"""Application configuration"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS settings - allow all origins for mobile access
    cors_origins: list[str] = ["*"]

    # Observer settings
    poll_interval: float = 0.1  # seconds between output polls
    discovery_interval: float = 5.0  # seconds between pane discovery
    capture_lines: int = 200  # number of lines to capture from pane

    # tmux settings
    tmux_socket: str | None = None  # optional tmux socket path

    model_config = {
        "env_prefix": "MOBILEAGENT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
