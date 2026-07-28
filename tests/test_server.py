import os

import pytest
from mcp import Client

from mcp_stateless.server import create_server


@pytest.mark.asyncio
async def test_echo_instance_reports_worker_pid() -> None:
    async with Client(create_server()) as client:
        result = await client.call_tool("echo_instance", {"message": "hello"})

    assert result.structured_content == {
        "message": "hello",
        "pid": os.getpid(),
        "protocol_version": "2026-07-28",
    }
