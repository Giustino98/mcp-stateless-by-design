import argparse
import asyncio
from dataclasses import dataclass

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import JSONRPCRequest, jsonrpc_message_adapter
from mcp_types.version import LATEST_MODERN_VERSION


@dataclass(frozen=True)
class Exchange:
    rpc_method: str
    worker_pid: int
    protocol_version: str
    has_session_id: bool


def parse_exchange(response: httpx2.Response) -> Exchange:
    message = jsonrpc_message_adapter.validate_json(response.request.content)
    if not isinstance(message, JSONRPCRequest):
        raise ValueError("Expected a JSON-RPC request")
    return Exchange(
        rpc_method=message.method,
        worker_pid=int(response.headers["x-worker-pid"]),
        protocol_version=response.request.headers["mcp-protocol-version"],
        has_session_id=(
            "mcp-session-id" in response.request.headers
            or "mcp-session-id" in response.headers
        ),
    )


async def run(url: str, calls: int) -> int:
    exchanges: list[Exchange] = []
    errors: dict[int, str] = {}

    async def record(response: httpx2.Response) -> None:
        exchanges.append(parse_exchange(response))

    async with httpx2.AsyncClient(
        limits=httpx2.Limits(max_connections=1, max_keepalive_connections=0),
        event_hooks={"response": [record]},
        timeout=3,
    ) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(transport, mode=LATEST_MODERN_VERSION) as client:
            for number in range(1, calls + 1):
                try:
                    result = await client.call_tool(
                        "echo_instance",
                        {"message": f"call-{number}"},
                    )
                except MCPError as error:
                    errors[number] = str(error)
                    continue
                if result.is_error:
                    errors[number] = str(result.content)

    print("Scenario 3 - Modern stateless")
    print(f"Running {calls} self-contained tool calls across four workers.\n")
    tool_calls = [
        exchange for exchange in exchanges if exchange.rpc_method == "tools/call"
    ]
    for number, exchange in enumerate(tool_calls, start=1):
        session = "present" if exchange.has_session_id else "none"
        status = "FAILED" if number in errors else "SUCCESS"
        print(
            f"{number:02}  worker={exchange.worker_pid}  "
            f"protocol={exchange.protocol_version}  session={session}  {status}"
        )
        if number in errors:
            print(f"    {errors[number]}")

    worker_pids = {exchange.worker_pid for exchange in tool_calls}
    initialize_requests = sum(
        exchange.rpc_method == "initialize" for exchange in exchanges
    )
    schema_lookups = sum(exchange.rpc_method == "tools/list" for exchange in exchanges)
    session_headers = sum(exchange.has_session_id for exchange in exchanges)
    unexpected_methods = {
        exchange.rpc_method
        for exchange in exchanges
        if exchange.rpc_method not in {"tools/call", "tools/list"}
    }
    print("\nSummary")
    print(f"  successful calls: {calls - len(errors)}/{calls}")
    print(f"  worker PIDs: {sorted(worker_pids)}")
    print(f"  initialize requests: {initialize_requests}")
    print(f"  schema lookups: {schema_lookups}")
    print(f"  session headers: {session_headers}")

    if errors:
        print(f"FAIL: {len(errors)} tool calls failed.")
        return 1
    if len(tool_calls) != calls:
        print(
            f"FAIL: expected {calls} tools/call requests, received {len(tool_calls)}."
        )
        return 1
    if len(worker_pids) < 2:
        print("FAIL: expected multiple workers to handle the requests.")
        return 1
    if initialize_requests or session_headers or unexpected_methods:
        print("FAIL: modern requests must not use initialization or session IDs.")
        return 1
    print("PASS: multiple workers handled self-contained calls without affinity.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8020/mcp")
    parser.add_argument("--calls", type=int, default=80)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.calls)))


if __name__ == "__main__":
    main()
