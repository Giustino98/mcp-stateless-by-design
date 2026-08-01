import argparse
import asyncio
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


async def run(url: str, attempts: int) -> int:
    print("Scenario 4 - MRTR with ephemeral worker keys")
    print(f"Running {attempts} two-round tool calls without affinity.\n")
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        if result.succeeded:
            status = "SUCCESS"
        elif result.error == INVALID_REQUEST_STATE:
            status = "INVALID REQUEST STATE"
        else:
            status = "UNEXPECTED ERROR"
        print(
            f"{result.number:02}  first={result.first.worker_pid}  "
            f"retry={result.retry.worker_pid}  {status}"
        )

    worker_pids = {
        exchange.worker_pid
        for result in results
        for exchange in (result.first, result.retry)
    }
    successes = sum(result.succeeded for result in results)
    failures = sum(result.error == INVALID_REQUEST_STATE for result in results)
    unexpected = attempts - successes - failures
    invalid_rounds = sum(
        result.first.has_request_state
        or result.first.has_input_responses
        or not result.retry.has_request_state
        or not result.retry.has_input_responses
        or result.first.has_session_id
        or result.retry.has_session_id
        for result in results
    )
    wrong_routes = sum(
        (result.succeeded and result.first.worker_pid != result.retry.worker_pid)
        or (
            result.error == INVALID_REQUEST_STATE
            and result.first.worker_pid == result.retry.worker_pid
        )
        for result in results
    )

    print("\nSummary")
    print(f"  successful retries: {successes}/{attempts}")
    print(f"  invalid requestState: {failures}")
    print(f"  worker PIDs: {sorted(worker_pids)}")
    print(f"  malformed round trips: {invalid_rounds}")

    if unexpected or invalid_rounds or wrong_routes:
        print("FAIL: observed an unexpected MRTR result.")
        return 1
    if len(worker_pids) < 2 or successes == 0 or failures == 0:
        print("FAIL: expected both same-worker successes and cross-worker failures.")
        return 1
    print("PASS: requestState works only when the retry reaches its original worker.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8030/mcp")
    parser.add_argument("--attempts", type=int, default=80)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts)))


if __name__ == "__main__":
    main()
