"""Tests for PaneRegistry service"""
import pytest

from app.models.input import InputRequest, InputType
from app.models.pane import PaneState, PaneStatus
from app.services.registry import PaneRegistry


@pytest.fixture
def registry() -> PaneRegistry:
    return PaneRegistry()


@pytest.fixture
def sample_pane() -> PaneState:
    return PaneState(
        pane_id="%0",
        session_name="test-session",
        window_name="main",
        window_index=0,
        pane_index=0,
        title="test",
        status=PaneStatus.RUNNING,
    )


class TestPaneRegistry:
    """Tests for PaneRegistry"""

    async def test_update_and_get(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test adding and retrieving a pane"""
        await registry.update(sample_pane.pane_id, sample_pane)

        result = await registry.get(sample_pane.pane_id)

        assert result is not None
        assert result.pane_id == sample_pane.pane_id
        assert result.session_name == sample_pane.session_name

    async def test_get_nonexistent(self, registry: PaneRegistry):
        """Test getting a nonexistent pane"""
        result = await registry.get("%999")

        assert result is None

    async def test_get_all(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test getting all panes"""
        await registry.update("%0", sample_pane)
        sample_pane2 = sample_pane.model_copy()
        sample_pane2.pane_id = "%1"
        await registry.update("%1", sample_pane2)

        result = await registry.get_all()

        assert len(result) == 2
        pane_ids = {p.pane_id for p in result}
        assert pane_ids == {"%0", "%1"}

    async def test_remove(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test removing a pane"""
        await registry.update(sample_pane.pane_id, sample_pane)

        removed = await registry.remove(sample_pane.pane_id)
        result = await registry.get(sample_pane.pane_id)

        assert removed is True
        assert result is None

    async def test_remove_nonexistent(self, registry: PaneRegistry):
        """Test removing a nonexistent pane"""
        removed = await registry.remove("%999")

        assert removed is False

    async def test_update_output(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test updating pane output"""
        await registry.update(sample_pane.pane_id, sample_pane)

        changed = await registry.update_output(
            sample_pane.pane_id,
            ["line1", "line2"],
            "newhash123",
        )

        assert changed is True

        pane = await registry.get(sample_pane.pane_id)
        assert pane is not None
        assert pane.last_lines == ["line1", "line2"]
        assert pane.last_output_hash == "newhash123"

    async def test_update_output_no_change(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test updating output with same hash"""
        sample_pane.last_output_hash = "samehash"
        await registry.update(sample_pane.pane_id, sample_pane)

        changed = await registry.update_output(
            sample_pane.pane_id,
            ["line1"],
            "samehash",
        )

        assert changed is False

    async def test_update_status(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test updating pane status"""
        await registry.update(sample_pane.pane_id, sample_pane)

        changed = await registry.update_status(
            sample_pane.pane_id,
            PaneStatus.WAITING_INPUT,
        )

        assert changed is True

        pane = await registry.get(sample_pane.pane_id)
        assert pane is not None
        assert pane.status == PaneStatus.WAITING_INPUT

    async def test_set_input_request(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test setting input request"""
        await registry.update(sample_pane.pane_id, sample_pane)

        request = InputRequest(input_type=InputType.TEXT, prompt="Enter value:")
        await registry.set_input_request(sample_pane.pane_id, request)

        pane = await registry.get(sample_pane.pane_id)
        assert pane is not None
        assert pane.input_request == request
        assert pane.status == PaneStatus.WAITING_INPUT

    async def test_clear_input_request(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test clearing input request"""
        sample_pane.status = PaneStatus.WAITING_INPUT
        sample_pane.input_request = InputRequest(input_type=InputType.TEXT)
        await registry.update(sample_pane.pane_id, sample_pane)

        await registry.clear_input_request(sample_pane.pane_id)

        pane = await registry.get(sample_pane.pane_id)
        assert pane is not None
        assert pane.input_request is None
        assert pane.status == PaneStatus.RUNNING

    async def test_get_pane_ids(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test getting all pane IDs"""
        await registry.update("%0", sample_pane)
        sample_pane2 = sample_pane.model_copy()
        sample_pane2.pane_id = "%1"
        await registry.update("%1", sample_pane2)

        ids = await registry.get_pane_ids()

        assert ids == {"%0", "%1"}

    async def test_clear(self, registry: PaneRegistry, sample_pane: PaneState):
        """Test clearing all panes"""
        await registry.update(sample_pane.pane_id, sample_pane)

        await registry.clear()

        result = await registry.get_all()
        assert len(result) == 0
