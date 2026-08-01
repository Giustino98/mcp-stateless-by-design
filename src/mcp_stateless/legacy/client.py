from dataclasses import dataclass

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import JSONRPCNotification, JSONRPCRequest, jsonrpc_message_adapter

SESSION_NOT_FOUND = "Session not found"


@dataclass(frozen=True)
class Exchange:
    rpc_method: str
    status_code: int
    worker_pid: int
    session_id: str


@dataclass(frozen=True)
class Attempt:
    number: int
    exchanges: tuple[Exchange, ...]
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def _rpc_method(body: bytes) -> str:
    message = jsonrpc_message_adapter.validate_json(body)
    if not isinstance(message, JSONRPCRequest | JSONRPCNotification):
        raise ValueError("Expected a JSON-RPC request or notification")
    return message.method


def _session_id(response: httpx2.Response) -> str:
    if "mcp-session-id" in response.headers:
        return response.headers["mcp-session-id"]
    return response.request.headers["mcp-session-id"]


def parse_exchange(response: httpx2.Response) -> Exchange:
    return Exchange(
        rpc_method=_rpc_method(response.request.content),
        status_code=response.status_code,
        worker_pid=int(response.headers["x-worker-pid"]),
        session_id=_session_id(response),
    )


async def run_attempt(url: str, number: int) -> Attempt:
    exchanges: list[Exchange] = []

    async def record(response: httpx2.Response) -> None:
        exchanges.append(parse_exchange(response))

    async with httpx2.AsyncClient(
        limits=httpx2.Limits(max_connections=1, max_keepalive_connections=0),
        event_hooks={"response": [record]},
        timeout=3,
    ) as http_client:
        transport = streamable_http_client(
            url,
            http_client=http_client,
            terminate_on_close=False,
        )
        async with Client(transport, mode="legacy") as client:
            try:
                result = await client.call_tool(
                    "echo_instance",
                    {"message": f"attempt-{number}"},
                )
            except MCPError as error:
                return Attempt(number, tuple(exchanges), str(error))
            error = str(result.content) if result.is_error else None
            return Attempt(number, tuple(exchanges), error)


def format_exchange(exchange: Exchange) -> str:
    return (
        f"{exchange.rpc_method}@pid:{exchange.worker_pid}"
        f" status:{exchange.status_code} session:{exchange.session_id}"
    )
