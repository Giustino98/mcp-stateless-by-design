import os

import pytest
from mcp import Client

from mcp_stateless.mrtr_server import create_server
from mcp_stateless.scenarios.mrtr_ephemeral_keys import accept_confirmation


@pytest.mark.asyncio
async def test_provisions_after_confirmation() -> None:
    async with Client(
        create_server(),
        elicitation_callback=accept_confirmation,
    ) as client:
        result = await client.call_tool(
            "provision_environment",
            {"name": "demo", "size": "small"},
        )

    assert result.structured_content == {
        "environment": "demo",
        "size": "small",
        "pid": os.getpid(),
    }
