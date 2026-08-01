import os

import pytest
from mcp import Client
from mcp.server.mcpserver import RequestStateSecurity
from mcp_types import CallToolResult, ElicitResult, InputRequiredResult, InputResponses

from mcp_stateless.mrtr_client import accept_confirmation
from mcp_stateless.mrtr_server import create_server

SHARED_KEY = "0123456789abcdef0123456789abcdef"


def shared_security() -> RequestStateSecurity:
    return RequestStateSecurity(
        keys=[SHARED_KEY],
        audience="mrtr-provisioning",
    )


@pytest.mark.asyncio
async def test_provisions_after_confirmation() -> None:
    async with Client(
        create_server(RequestStateSecurity.ephemeral()),
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


@pytest.mark.asyncio
async def test_resumes_on_another_server_with_shared_key() -> None:
    arguments = {"name": "demo", "size": "small"}
    async with Client(
        create_server(shared_security()),
        elicitation_callback=accept_confirmation,
    ) as client:
        first = await client.session.call_tool(
            "provision_environment",
            arguments,
            allow_input_required=True,
        )

    assert isinstance(first, InputRequiredResult)
    assert first.input_requests is not None
    assert first.request_state is not None
    responses: InputResponses = {
        next(iter(first.input_requests)): ElicitResult(
            action="accept",
            content={"confirmed": True},
        )
    }

    async with Client(
        create_server(shared_security()),
        elicitation_callback=accept_confirmation,
    ) as client:
        result = await client.session.call_tool(
            "provision_environment",
            arguments,
            input_responses=responses,
            request_state=first.request_state,
            allow_input_required=True,
        )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
