from dataclasses import dataclass

import httpx2
from mcp import Client
from mcp.client.session import ClientRequestContext
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import (
    ElicitRequestParams,
    ElicitResult,
    JSONRPCRequest,
    jsonrpc_message_adapter,
)
from mcp_types.version import LATEST_MODERN_VERSION

INVALID_REQUEST_STATE = "Invalid or expired requestState"


@dataclass(frozen=True)
class Exchange:
    rpc_method: str
    worker_pid: int
    has_request_state: bool
    has_input_responses: bool
    has_session_id: bool


@dataclass(frozen=True)
class Attempt:
    number: int
    first: Exchange
    retry: Exchange
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None

    @property
    def is_well_formed(self) -> bool:
        return (
            not self.first.has_request_state
            and not self.first.has_input_responses
            and self.retry.has_request_state
            and self.retry.has_input_responses
            and not self.first.has_session_id
            and not self.retry.has_session_id
        )


def parse_exchange(response: httpx2.Response) -> Exchange:
    message = jsonrpc_message_adapter.validate_json(response.request.content)
    if not isinstance(message, JSONRPCRequest):
        raise ValueError("Expected a JSON-RPC request")
    params = message.params or {}
    return Exchange(
        rpc_method=message.method,
        worker_pid=int(response.headers["x-worker-pid"]),
        has_request_state="requestState" in params,
        has_input_responses="inputResponses" in params,
        has_session_id=(
            "mcp-session-id" in response.request.headers
            or "mcp-session-id" in response.headers
        ),
    )


async def accept_confirmation(
    context: ClientRequestContext,
    params: ElicitRequestParams,
) -> ElicitResult:
    return ElicitResult(action="accept", content={"confirmed": True})


async def run_attempt(url: str, number: int) -> Attempt:
    exchanges: list[Exchange] = []

    async def record(response: httpx2.Response) -> None:
        exchanges.append(parse_exchange(response))

    async with httpx2.AsyncClient(
        limits=httpx2.Limits(max_connections=1, max_keepalive_connections=0),
        event_hooks={"response": [record]},
        timeout=3,
    ) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(
            transport,
            mode=LATEST_MODERN_VERSION,
            elicitation_callback=accept_confirmation,
        ) as client:
            try:
                result = await client.call_tool(
                    "provision_environment",
                    {"name": f"demo-{number}", "size": "small"},
                )
            except MCPError as error:
                failure = error.message
            else:
                failure = str(result.content) if result.is_error else None

    first, retry = (
        exchange for exchange in exchanges if exchange.rpc_method == "tools/call"
    )
    return Attempt(number, first, retry, failure)
