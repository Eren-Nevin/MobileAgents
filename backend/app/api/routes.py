"""REST API routes"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ..models.input import InputSubmission
from ..models.pane import PaneInfo, PaneOutput, PaneStatus
from ..services.registry import PaneRegistry
from ..services.tmux import TmuxService
from .deps import get_registry, get_tmux_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["panes"])


@router.get("/panes", response_model=list[PaneInfo])
async def list_panes(
    registry: Annotated[PaneRegistry, Depends(get_registry)],
) -> list[PaneInfo]:
    """
    List all tracked panes.

    Returns list of panes with their current status.
    """
    panes = await registry.get_all()
    return [pane.to_info() for pane in panes]


@router.get("/panes/{pane_id}", response_model=PaneInfo)
async def get_pane(
    pane_id: str,
    registry: Annotated[PaneRegistry, Depends(get_registry)],
) -> PaneInfo:
    """
    Get details for a specific pane.

    Args:
        pane_id: Pane identifier (e.g., '%3')
    """
    pane = await registry.get(pane_id)
    if not pane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pane {pane_id} not found",
        )
    return pane.to_info()


@router.get("/panes/{pane_id}/output", response_model=PaneOutput)
async def get_pane_output(
    pane_id: str,
    registry: Annotated[PaneRegistry, Depends(get_registry)],
    tmux: Annotated[TmuxService, Depends(get_tmux_service)],
    lines: int = 500,
    refresh: bool = False,
) -> PaneOutput:
    """
    Get output from a pane.

    Args:
        pane_id: Pane identifier
        lines: Number of lines to return (default 500)
        refresh: If True, capture fresh output from tmux
    """
    pane = await registry.get(pane_id)
    if not pane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pane {pane_id} not found",
        )

    if refresh:
        # Capture fresh output
        output_lines = await tmux.capture_pane(pane_id, lines)
    else:
        # Use cached output
        output_lines = pane.last_lines[-lines:] if pane.last_lines else []

    # Get cursor position
    cursor_pos = await tmux.get_cursor_position(pane_id)
    cursor_x, cursor_y = cursor_pos if cursor_pos else (0, 0)

    return PaneOutput(
        pane_id=pane_id,
        lines=output_lines,
        line_count=len(output_lines),
        input_request=pane.input_request,
        cursor_x=cursor_x,
        cursor_y=cursor_y,
    )


@router.post("/panes/{pane_id}/input", status_code=status.HTTP_200_OK)
async def send_input(
    pane_id: str,
    submission: InputSubmission,
    registry: Annotated[PaneRegistry, Depends(get_registry)],
    tmux: Annotated[TmuxService, Depends(get_tmux_service)],
) -> dict:
    """
    Send input to a pane.

    Only allowed when pane is waiting for input.

    Args:
        pane_id: Pane identifier
        submission: Input value to send
    """
    pane = await registry.get(pane_id)
    if not pane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pane {pane_id} not found",
        )

    # Check pane is waiting for input
    if pane.status != PaneStatus.WAITING_INPUT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pane {pane_id} is not waiting for input (status: {pane.status})",
        )

    # Validate input type matches
    if pane.input_request and pane.input_request.input_type != submission.input_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input type mismatch: expected {pane.input_request.input_type}, got {submission.input_type}",
        )

    # Send the input
    success = await tmux.send_keys(pane_id, submission.value)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send input to pane {pane_id}",
        )

    # Clear the input request
    await registry.clear_input_request(pane_id)

    logger.info(f"Input sent to pane {pane_id}: {submission.value[:50]}...")

    return {"status": "ok", "pane_id": pane_id}


@router.post("/panes/{pane_id}/keys", status_code=status.HTTP_200_OK)
async def send_keys(
    pane_id: str,
    body: dict,
    registry: Annotated[PaneRegistry, Depends(get_registry)],
    tmux: Annotated[TmuxService, Depends(get_tmux_service)],
) -> dict:
    """
    Send raw keys to a pane (always allowed).

    Args:
        pane_id: Pane identifier
        body: {"keys": "text to send", "enter": true/false}
    """
    pane = await registry.get(pane_id)
    if not pane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pane {pane_id} not found",
        )

    keys = body.get("keys", "")
    send_enter = body.get("enter", True)
    literal = body.get("literal", True)

    success = await tmux.send_keys(pane_id, keys, enter=send_enter, literal=literal)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send keys to pane {pane_id}",
        )

    logger.info(f"Keys sent to pane {pane_id}: {keys[:50]}...")
    return {"status": "ok", "pane_id": pane_id}


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "healthy"}
