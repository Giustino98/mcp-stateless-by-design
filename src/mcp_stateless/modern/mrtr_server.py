import os
from typing import Annotated, TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Elicit, RequestStateSecurity, Resolve
from pydantic import BaseModel

from mcp_stateless.worker_pid import WorkerPidMiddleware


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


def create_server(request_state_security: RequestStateSecurity) -> MCPServer:
    server = MCPServer(
        "mrtr-provisioning",
        request_state_security=request_state_security,
    )

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


server = create_server(RequestStateSecurity.ephemeral())
app = WorkerPidMiddleware(server.streamable_http_app())
