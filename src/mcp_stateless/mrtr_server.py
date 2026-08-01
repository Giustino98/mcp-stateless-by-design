import os
from typing import Annotated, TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Elicit, Resolve
from pydantic import BaseModel

from mcp_stateless.server import WorkerHeaderMiddleware


class Confirmation(BaseModel):
    confirmed: bool


class ProvisionResult(TypedDict):
    environment: str
    size: str
    pid: int


def request_confirmation() -> Elicit[Confirmation]:
    return Elicit(
        "This environment will cost EUR 120 per month. Continue?",
        Confirmation,
    )


def create_server() -> MCPServer:
    server = MCPServer("mrtr-provisioning")

    def provision_environment(
        name: str,
        size: str,
        confirmation: Annotated[Confirmation, Resolve(request_confirmation)],
    ) -> ProvisionResult:
        if not confirmation.confirmed:
            raise ValueError("Provisioning was not confirmed")
        return ProvisionResult(environment=name, size=size, pid=os.getpid())

    server.add_tool(provision_environment)
    return server


server = create_server()
app = WorkerHeaderMiddleware(server.streamable_http_app())
