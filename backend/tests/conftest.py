"""Pytest fixtures for backend tests"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.services.observer import ObserverDaemon
from app.services.parser import InputParser
from app.services.registry import PaneRegistry
from app.services.tmux import TmuxPane, TmuxService


@pytest.fixture
def mock_tmux_service() -> MagicMock:
    """Create a mock TmuxService"""
    service = MagicMock(spec=TmuxService)
    service.is_available = AsyncMock(return_value=True)
    service.list_sessions = AsyncMock(return_value=["test-session"])
    service.list_windows = AsyncMock(return_value=[{"index": 0, "name": "main"}])
    service.list_panes = AsyncMock(return_value=[
        TmuxPane(
            pane_id="%0",
            session_name="test-session",
            window_name="main",
            window_index=0,
            pane_index=0,
            pane_title="test",
            pane_active=True,
        )
    ])
    service.discover_all_panes = AsyncMock(return_value=[
        TmuxPane(
            pane_id="%0",
            session_name="test-session",
            window_name="main",
            window_index=0,
            pane_index=0,
            pane_title="test",
            pane_active=True,
        )
    ])
    service.capture_pane = AsyncMock(return_value=["line 1", "line 2", "line 3"])
    service.send_keys = AsyncMock(return_value=True)
    return service


@pytest.fixture
def registry() -> PaneRegistry:
    """Create a fresh PaneRegistry"""
    return PaneRegistry()


@pytest.fixture
def parser() -> InputParser:
    """Create an InputParser"""
    return InputParser()


@pytest.fixture
def observer(mock_tmux_service: MagicMock, registry: PaneRegistry, parser: InputParser) -> ObserverDaemon:
    """Create an ObserverDaemon with mocked dependencies"""
    return ObserverDaemon(
        tmux_service=mock_tmux_service,
        registry=registry,
        parser=parser,
        poll_interval=0.1,
        discovery_interval=0.5,
    )


@pytest.fixture
def test_client(mock_tmux_service: MagicMock, registry: PaneRegistry, observer: ObserverDaemon) -> TestClient:
    """Create a test client with mocked services"""
    deps.set_services(mock_tmux_service, registry, observer)
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(
    mock_tmux_service: MagicMock,
    registry: PaneRegistry,
    observer: ObserverDaemon,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client"""
    deps.set_services(mock_tmux_service, registry, observer)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
