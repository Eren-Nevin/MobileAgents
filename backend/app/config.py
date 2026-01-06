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

    # Control mode settings (real-time streaming)
    use_control_mode: bool = True  # Use tmux control mode for real-time updates
    control_mode_reconnect_delay: float = 1.0  # Initial reconnect delay in seconds
    control_mode_max_reconnects: int = 5  # Max reconnection attempts

    # Observer settings (fallback polling when control mode is disabled)
    poll_interval: float = 1.0  # seconds between output polls (increased, fallback only)
    discovery_interval: float = 5.0  # seconds between pane discovery
    capture_lines: int = 500  # number of lines to capture from pane

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
