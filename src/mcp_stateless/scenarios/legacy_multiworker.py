import argparse
import asyncio

from mcp_stateless.legacy_client import (
    SESSION_NOT_FOUND,
    format_exchange,
    run_attempt,
)


async def run(url: str, attempts: int) -> int:
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        if result.succeeded:
            status = "SUCCESS"
        elif result.error == SESSION_NOT_FOUND:
            status = "SESSION NOT FOUND"
        else:
            status = "UNEXPECTED ERROR"
        route = " -> ".join(format_exchange(item) for item in result.exchanges)
        print(f"{result.number:02} {status:<17} {route}")
        if result.error is not None:
            print(f"   {result.error}")

    worker_pids = {
        exchange.worker_pid for result in results for exchange in result.exchanges
    }
    successes = sum(result.succeeded for result in results)
    failures = sum(result.error == SESSION_NOT_FOUND for result in results)
    unexpected = attempts - successes - failures
    print(
        f"\nworkers={sorted(worker_pids)} "
        f"successes={successes} session_not_found={failures} unexpected={unexpected}"
    )

    if unexpected:
        print("Expected only successful calls and Session not found failures.")
        return 1
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
    parser.add_argument("--attempts", type=int, default=80)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts)))


if __name__ == "__main__":
    main()
