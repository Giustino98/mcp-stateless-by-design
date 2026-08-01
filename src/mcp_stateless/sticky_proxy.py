import asyncio
from collections.abc import AsyncIterator, Mapping

import httpx2
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route

SESSION_HEADER = "mcp-session-id"
HOP_BY_HOP_HEADERS = {"connection", "content-length", "host", "transfer-encoding"}


class StickyRouter:
    def __init__(self, upstreams: tuple[str, ...]) -> None:
        self._upstreams = upstreams
        self._sessions: dict[str, str] = {}
        self._next_upstream = 0

    def route(self, session_id: str | None) -> str:
        if session_id is not None:
            return self._sessions[session_id]
        upstream = self._upstreams[self._next_upstream]
        self._next_upstream = (self._next_upstream + 1) % len(self._upstreams)
        return upstream

    def bind(self, session_id: str, upstream: str) -> None:
        self._sessions[session_id] = upstream


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS
    }


def create_proxy(upstreams: tuple[str, ...]) -> Starlette:
    router = StickyRouter(upstreams)

    async def forward(request: Request) -> Response:
        session_id = request.headers.get(SESSION_HEADER)
        try:
            upstream = router.route(session_id)
        except KeyError:
            return PlainTextResponse("Unknown session", status_code=404)

        url = f"{upstream}{request.url.path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"

        client = httpx2.AsyncClient(timeout=None)
        upstream_request = client.build_request(
            request.method,
            url,
            headers=_headers(request.headers),
            content=await request.body(),
        )
        try:
            upstream_response = await client.send(upstream_request, stream=True)
        except BaseException:
            await client.aclose()
            raise

        created_session = upstream_response.headers.get(SESSION_HEADER)
        if created_session is not None:
            router.bind(created_session, upstream)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream_response.aiter_raw():
                    yield chunk
            finally:
                await upstream_response.aclose()
                await client.aclose()

        return StreamingResponse(
            body(),
            status_code=upstream_response.status_code,
            headers=_headers(upstream_response.headers),
        )

    return Starlette(routes=[Route("/mcp", forward, methods=["GET", "POST", "DELETE"])])


app = create_proxy(("http://127.0.0.1:8001", "http://127.0.0.1:8002"))


def _selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()


def main() -> None:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8010,
        loop="none",
        access_log=False,
    )
    asyncio.run(uvicorn.Server(config).serve(), loop_factory=_selector_loop)


if __name__ == "__main__":
    main()
