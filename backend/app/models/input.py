"""Input-related Pydantic models"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InputType(str, Enum):
    """Type of input required from user"""
    TEXT = "text"
    CHOICE = "choice"
    CONFIRM = "confirm"


class InputRequest(BaseModel):
    """Parsed [INPUT_REQUIRED] block from pane output"""
    input_type: InputType = Field(..., description="Type of input expected")
    prompt: Optional[str] = Field(None, description="Prompt text for text input")
    message: Optional[str] = Field(None, description="Message for confirmation")
    options: Optional[list[str]] = Field(None, description="Available choices for choice input")


class InputSubmission(BaseModel):
    """User input to be sent to a pane"""
    input_type: InputType = Field(..., description="Type of input being submitted")
    value: str = Field(..., description="The input value to send")
