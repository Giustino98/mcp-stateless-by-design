import argparse
import asyncio

from mcp_stateless.mrtr_client import INVALID_REQUEST_STATE, run_attempt


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
    invalid_rounds = sum(not result.is_well_formed for result in results)
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
