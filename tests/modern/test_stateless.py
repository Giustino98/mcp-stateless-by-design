import httpx2

from mcp_stateless.modern.stateless import Exchange, parse_exchange

BODY = b'{"jsonrpc":"2.0","id":1,"method":"tools/call"}'


def test_parses_stateless_exchange() -> None:
    request = httpx2.Request(
        "POST",
        "http://mcp.test",
        headers={"mcp-protocol-version": "2026-07-28"},
        content=BODY,
    )
    response = httpx2.Response(
        200,
        headers={"x-worker-pid": "101"},
        request=request,
    )

    assert parse_exchange(response) == Exchange(
        "tools/call",
        101,
        "2026-07-28",
        False,
    )
