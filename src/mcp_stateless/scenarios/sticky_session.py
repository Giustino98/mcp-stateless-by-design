import argparse
import asyncio

from mcp_stateless.legacy_client import Attempt, format_exchange, run_attempt


def _print_attempt(attempt: Attempt, verbose: bool) -> None:
    status = "SUCCESS" if attempt.succeeded else "UNEXPECTED ERROR"
    if verbose:
        route = " -> ".join(format_exchange(item) for item in attempt.exchanges)
        print(f"{attempt.number:02} {status:<16} {route}")
    else:
        session = attempt.exchanges[0].session_id[:8]
        workers = ", ".join(
            str(pid) for pid in sorted({item.worker_pid for item in attempt.exchanges})
        )
        print(
            f"{attempt.number:02}  session={session}  worker={workers:<12} "
            f"requests={len(attempt.exchanges)}  {status}"
        )
    if attempt.error is not None:
        print(f"    {attempt.error}")


async def run(url: str, attempts: int, verbose: bool) -> int:
    print("Scenario 2 - Legacy sticky session")
    print(f"Running {attempts} independent sessions through the sticky proxy.\n")
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        _print_attempt(result, verbose)

    worker_pids = {
        exchange.worker_pid for result in results for exchange in result.exchanges
    }
    crossed_sessions = sum(
        len({exchange.worker_pid for exchange in result.exchanges}) != 1
        for result in results
    )
    failures = sum(not result.succeeded for result in results)
    print("\nSummary")
    print(f"  successful sessions: {attempts - failures}/{attempts}")
    print(f"  worker PIDs: {sorted(worker_pids)}")
    print(f"  affinity violations: {crossed_sessions}")

    if failures or crossed_sessions:
        print("FAIL: expected every session to stay on one worker and succeed.")
        return 1
    if len(worker_pids) != 2:
        print("FAIL: expected both replicas to handle sessions.")
        return 1
    print("PASS: sticky routing kept every session on its assigned replica.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8010/mcp")
    parser.add_argument("--attempts", type=int, default=80)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts, args.verbose)))


if __name__ == "__main__":
    main()
