import argparse
import asyncio

from mcp_stateless.mrtr_client import run_attempt


async def run(url: str, attempts: int) -> int:
    print("Scenario 5 - MRTR with a shared worker key")
    print(f"Running {attempts} two-round tool calls without affinity.\n")
    results = [await run_attempt(url, number) for number in range(1, attempts + 1)]

    for result in results:
        route = (
            "CROSS-WORKER"
            if result.first.worker_pid != result.retry.worker_pid
            else "SAME-WORKER"
        )
        status = "SUCCESS" if result.succeeded else "FAILED"
        print(
            f"{result.number:02}  first={result.first.worker_pid}  "
            f"retry={result.retry.worker_pid}  {route} {status}"
        )

    worker_pids = {
        exchange.worker_pid
        for result in results
        for exchange in (result.first, result.retry)
    }
    successes = sum(result.succeeded for result in results)
    cross_worker = sum(
        result.first.worker_pid != result.retry.worker_pid for result in results
    )
    invalid_rounds = sum(not result.is_well_formed for result in results)

    print("\nSummary")
    print(f"  successful retries: {successes}/{attempts}")
    print(f"  cross-worker successes: {cross_worker}")
    print(f"  worker PIDs: {sorted(worker_pids)}")
    print(f"  malformed round trips: {invalid_rounds}")

    if successes != attempts or invalid_rounds:
        print("FAIL: expected every MRTR retry to succeed.")
        return 1
    if len(worker_pids) < 2 or cross_worker == 0:
        print("FAIL: expected successful retries across different workers.")
        return 1
    print("PASS: cross-worker retries verified requestState without affinity.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8040/mcp")
    parser.add_argument("--attempts", type=int, default=80)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.attempts)))


if __name__ == "__main__":
    main()
