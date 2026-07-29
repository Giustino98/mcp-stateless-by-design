import os
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class EchoResult(TypedDict):
    message: str
    pid: int
    protocol_version: str


class WorkerHeaderMiddleware:
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


def create_server() -> MCPServer:
    server = MCPServer("mcp-stateless-by-design")

    def echo_instance(message: str, context: Context[object, object]) -> EchoResult:
        return EchoResult(
            message=message,
            pid=os.getpid(),
            protocol_version=context.request_context.protocol_version,
        )

    server.add_tool(echo_instance)
    return server


server = create_server()
app = WorkerHeaderMiddleware(server.streamable_http_app())
