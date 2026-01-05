"""Tests for InputParser service"""
import pytest

from app.models.input import InputType
from app.services.parser import InputParser


@pytest.fixture
def parser() -> InputParser:
    return InputParser()


class TestInputParser:
    """Tests for InputParser"""

    def test_parse_text_input(self, parser: InputParser):
        """Test parsing text input request"""
        lines = [
            "Some output",
            "[INPUT_REQUIRED]",
            "TYPE: text",
            "PROMPT: Enter your name:",
            "",
            "More output",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.TEXT
        assert result.prompt == "Enter your name:"

    def test_parse_choice_input(self, parser: InputParser):
        """Test parsing choice input request"""
        lines = [
            "[INPUT_REQUIRED]",
            "TYPE: choice",
            "OPTIONS:",
            "1) Yes",
            "2) No",
            "3) Maybe",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.CHOICE
        assert result.options == ["Yes", "No", "Maybe"]

    def test_parse_confirm_input(self, parser: InputParser):
        """Test parsing confirm input request"""
        lines = [
            "[INPUT_REQUIRED]",
            "TYPE: confirm",
            "MESSAGE: Deploy to production?",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.CONFIRM
        assert result.message == "Deploy to production?"

    def test_parse_no_marker(self, parser: InputParser):
        """Test parsing when no marker present"""
        lines = ["Normal output", "More output"]

        result = parser.parse(lines)

        assert result is None

    def test_parse_marker_at_end(self, parser: InputParser):
        """Test parsing when marker is at the end"""
        lines = [
            "Lots of output",
            "More output",
            "[INPUT_REQUIRED]",
            "TYPE: text",
            "PROMPT: Enter value:",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.TEXT

    def test_has_input_marker_true(self, parser: InputParser):
        """Test has_input_marker when marker present"""
        lines = ["output", "[INPUT_REQUIRED]", "TYPE: text"]

        assert parser.has_input_marker(lines) is True

    def test_has_input_marker_false(self, parser: InputParser):
        """Test has_input_marker when marker absent"""
        lines = ["output", "more output"]

        assert parser.has_input_marker(lines) is False

    def test_parse_infers_type_from_options(self, parser: InputParser):
        """Test that type is inferred from OPTIONS when TYPE missing"""
        lines = [
            "[INPUT_REQUIRED]",
            "OPTIONS:",
            "1) Option A",
            "2) Option B",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.CHOICE

    def test_parse_case_insensitive(self, parser: InputParser):
        """Test parsing is case insensitive"""
        lines = [
            "[INPUT_REQUIRED]",
            "type: TEXT",
            "prompt: Enter something:",
        ]

        result = parser.parse(lines)

        assert result is not None
        assert result.input_type == InputType.TEXT
