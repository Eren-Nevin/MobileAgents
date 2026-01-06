"""FastAPI application entry point"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import deps
from .api.routes import router as api_router
from .api.websocket import broadcast_event, router as ws_router
from .config import get_settings
from .services.observer import ObserverDaemon
from .services.parser import InputParser
from .services.registry import PaneRegistry
from .services.tmux import TmuxService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()

    # Initialize services
    logger.info("Initializing services...")

    tmux_service = TmuxService(socket_path=settings.tmux_socket)
    registry = PaneRegistry()
    parser = InputParser()
    observer = ObserverDaemon(
        tmux_service=tmux_service,
        registry=registry,
        parser=parser,
        use_control_mode=settings.use_control_mode,
        poll_interval=settings.poll_interval,
        discovery_interval=settings.discovery_interval,
        capture_lines=settings.capture_lines,
        control_mode_reconnect_delay=settings.control_mode_reconnect_delay,
        control_mode_max_reconnects=settings.control_mode_max_reconnects,
    )

    # Register WebSocket broadcast callback
    observer.on_event(broadcast_event)

    # Set global service instances for dependency injection
    deps.set_services(tmux_service, registry, observer)

    # Check tmux availability
    if await tmux_service.is_available():
        logger.info("tmux is available")
    else:
        logger.warning("tmux is not available or no sessions exist")

    # Start observer
    await observer.start()
    logger.info(f"Observer daemon started (mode: {observer.mode})")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await observer.stop()
    logger.info("Observer daemon stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="MobileAgent",
        description="tmux Agent Web Observer & Control App",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router)
    app.include_router(ws_router)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
