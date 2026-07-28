from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mcp_stateless.worker import pid


class WorkerHeaderMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_worker(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message["headers"])
                headers.append((b"x-worker-pid", str(pid()).encode()))
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_worker)
