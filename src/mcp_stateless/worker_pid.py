import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class WorkerPidMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def add_worker_pid(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message["headers"])
                headers.append((b"x-worker-pid", str(os.getpid()).encode()))
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, add_worker_pid)
