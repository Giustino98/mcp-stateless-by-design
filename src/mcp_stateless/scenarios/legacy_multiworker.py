import argparse
import asyncio
import re
from dataclasses import dataclass

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

RPC_METHOD_PATTERN = re.compile(rb'"method"\s*:\s*"([^"]+)"')


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
    match = RPC_METHOD_PATTERN.search(body)
    if match is None:
        raise ValueError("JSON-RPC request has no method")
    return match.group(1).decode()


def _session_id(response: httpx2.Response) -> str:
    if "mcp-session-id" in response.headers:
        return response.headers["mcp-session-id"]
    return response.request.headers["mcp-session-id"]


async def run_attempt(url: str, number: int) -> Attempt:
    exchanges: list[Exchange] = []

    async def record(response: httpx2.Response) -> None:
        exchanges.append(
            Exchange(
                rpc_method=_rpc_method(response.request.content),
                status_code=response.status_code,
                worker_pid=int(response.headers["x-worker-pid"]),
                session_id=_session_id(response),
            )
        )

    try:
        async with asyncio.timeout(5):
            limits = httpx2.Limits(max_connections=1, max_keepalive_connections=0)
            async with httpx2.AsyncClient(
                limits=limits,
                event_hooks={"response": [record]},
                timeout=3,
            ) as http_client:
                transport = streamable_http_client(
                    url,
                    http_client=http_client,
                    terminate_on_close=False,
                )
                async with Client(transport, mode="legacy") as client:
                    result = await client.call_tool(
                        "echo_instance",
                        {"message": f"attempt-{number}"},
                    )
                    if result.is_error:
                        return Attempt(number, tuple(exchanges), str(result.content))
                    return Attempt(number, tuple(exchanges), None)
    except MCPError as error:
        return Attempt(number, tuple(exchanges), str(error))


def _format_exchange(exchange: Exchange) -> str:
    return (
        f"{exchange.rpc_method}@pid:{exchange.worker_pid}"
        f" status:{exchange.status_code} session:{exchange.session_id}"
    )


async def run(url: str, attempts: int) -> int:
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        status = "SUCCESS" if result.succeeded else "SESSION NOT FOUND"
        route = " -> ".join(_format_exchange(item) for item in result.exchanges)
        print(f"{result.number:02} {status:<17} {route}")
        if result.error is not None:
            print(f"   {result.error}")

    worker_pids = {
        exchange.worker_pid for result in results for exchange in result.exchanges
    }
    successes = sum(result.succeeded for result in results)
    failures = attempts - successes
    print(
        f"\nworkers={sorted(worker_pids)} "
        f"successes={successes} session_not_found={failures}"
    )

    if len(worker_pids) < 2:
        print(
            "Expected multiple worker PIDs; the server did not distribute connections."
        )
        return 1
    if successes == 0 or failures == 0:
        print("Expected both successes and intermittent session failures.")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--attempts", type=int, default=40)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts)))


if __name__ == "__main__":
    main()
