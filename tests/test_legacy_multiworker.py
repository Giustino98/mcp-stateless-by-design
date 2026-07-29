import httpx2

from mcp_stateless.scenarios.legacy_multiworker import Exchange, parse_exchange

BODY = b'{"jsonrpc":"2.0","id":1,"method":"tools/call"}'


def test_parses_session_created_by_initialize_response() -> None:
    request = httpx2.Request("POST", "http://mcp.test", content=BODY)
    response = httpx2.Response(
        200,
        headers={"mcp-session-id": "session-1", "x-worker-pid": "101"},
        request=request,
    )

    assert parse_exchange(response) == Exchange("tools/call", 200, 101, "session-1")


def test_parses_session_carried_by_subsequent_request() -> None:
    request = httpx2.Request(
        "POST",
        "http://mcp.test",
        headers={"mcp-session-id": "session-1"},
        content=BODY,
    )
    response = httpx2.Response(
        404,
        headers={"x-worker-pid": "202"},
        request=request,
    )

    assert parse_exchange(response) == Exchange("tools/call", 404, 202, "session-1")
