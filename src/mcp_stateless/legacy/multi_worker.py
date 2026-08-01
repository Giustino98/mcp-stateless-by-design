import argparse
import asyncio

from mcp_stateless.legacy.client import (
    SESSION_NOT_FOUND,
    Attempt,
    format_exchange,
    run_attempt,
)


def _print_attempt(attempt: Attempt, verbose: bool) -> None:
    if attempt.succeeded:
        status = "SUCCESS"
    elif attempt.error == SESSION_NOT_FOUND:
        status = "SESSION NOT FOUND"
    else:
        status = "UNEXPECTED ERROR"
    if verbose:
        route = " -> ".join(format_exchange(item) for item in attempt.exchanges)
        print(f"{attempt.number:02} {status:<17} {route}")
    else:
        route = " -> ".join(str(item.worker_pid) for item in attempt.exchanges)
        session = attempt.exchanges[0].session_id[:8]
        print(f"{attempt.number:02}  session={session}  workers={route}  {status}")
    if attempt.error is not None and (verbose or attempt.error != SESSION_NOT_FOUND):
        print(f"    {attempt.error}")


async def run(url: str, attempts: int, verbose: bool) -> int:
    print("Scenario 1 - Legacy multi-worker failure")
    print(f"Running {attempts} independent sessions without affinity.\n")
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        _print_attempt(result, verbose)

    worker_pids = {
        exchange.worker_pid for result in results for exchange in result.exchanges
    }
    successes = sum(result.succeeded for result in results)
    failures = sum(result.error == SESSION_NOT_FOUND for result in results)
    unexpected = attempts - successes - failures
    print("\nSummary")
    print(f"  successful sessions: {successes}/{attempts}")
    print(f"  Session not found: {failures}")
    print(f"  worker PIDs: {sorted(worker_pids)}")
    print(f"  unexpected errors: {unexpected}")

    if unexpected:
        print("FAIL: expected only successes and Session not found failures.")
        return 1
    if len(worker_pids) < 2:
        print("FAIL: expected multiple workers to handle the requests.")
        return 1
    if successes == 0 or failures == 0:
        print("FAIL: expected both successes and intermittent session failures.")
        return 1
    print("PASS: random routing made legacy session failures intermittent.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--attempts", type=int, default=80)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts, args.verbose)))


if __name__ == "__main__":
    main()
