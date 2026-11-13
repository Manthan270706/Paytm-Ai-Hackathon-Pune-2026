import uuid

import pytest
from pydantic import BaseModel

from app.tools import ALL_TOOLS, TOOL_REGISTRY, ToolContext


def test_exactly_11_tools_registered() -> None:
    assert len(ALL_TOOLS) == 11
    assert len(TOOL_REGISTRY) == 11


def test_no_tool_schema_contains_merchant_id() -> None:
    """PRD §7.3 & Trust Rule #3: No tool input schema may contain merchant_id.

    The merchant scope must always be bound server-side from the authenticated session.
    """
    for tool in ALL_TOOLS:
        input_fields = tool.input_schema.model_fields.keys()
        assert "merchant_id" not in input_fields, (
            f"VIOLATION: Tool '{tool.name}' exposes 'merchant_id' in its input schema! "
            f"Fields found: {list(input_fields)}"
        )


def test_tool_schemas_are_pydantic_models() -> None:
    for tool in ALL_TOOLS:
        assert issubclass(tool.input_schema, BaseModel)
        assert issubclass(tool.output_schema, BaseModel)


@pytest.mark.asyncio
async def test_tool_stubs_raise_not_implemented() -> None:
    ctx = ToolContext(merchant_id=uuid.uuid4(), session=None)  # type: ignore[arg-type]
    for tool in ALL_TOOLS:
        # Instantiate empty or default model for stub test
        dummy_input = tool.input_schema.model_construct()
        with pytest.raises(NotImplementedError):
            await tool.runner(dummy_input, ctx)
