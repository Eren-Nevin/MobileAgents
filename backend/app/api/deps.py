"""API dependency injection"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.observer import ObserverDaemon
    from ..services.registry import PaneRegistry
    from ..services.tmux import TmuxService

# Global service instances (set by main.py on startup)
_tmux_service: "TmuxService | None" = None
_registry: "PaneRegistry | None" = None
_observer: "ObserverDaemon | None" = None


def set_services(
    tmux: "TmuxService",
    registry: "PaneRegistry",
    observer: "ObserverDaemon",
) -> None:
    """Set global service instances"""
    global _tmux_service, _registry, _observer
    _tmux_service = tmux
    _registry = registry
    _observer = observer


def get_tmux_service() -> "TmuxService":
    """Get TmuxService instance"""
    if _tmux_service is None:
        raise RuntimeError("TmuxService not initialized")
    return _tmux_service


def get_registry() -> "PaneRegistry":
    """Get PaneRegistry instance"""
    if _registry is None:
        raise RuntimeError("PaneRegistry not initialized")
    return _registry


def get_observer() -> "ObserverDaemon":
    """Get ObserverDaemon instance"""
    if _observer is None:
        raise RuntimeError("ObserverDaemon not initialized")
    return _observer
