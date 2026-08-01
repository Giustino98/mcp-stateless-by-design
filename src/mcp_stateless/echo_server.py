import os
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from mcp_stateless.worker_pid import WorkerPidMiddleware


class EchoResult(TypedDict):
    message: str
    pid: int
    protocol_version: str


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
app = WorkerPidMiddleware(server.streamable_http_app())
