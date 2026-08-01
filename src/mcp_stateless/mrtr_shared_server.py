import os

from mcp.server.mcpserver import RequestStateSecurity

from mcp_stateless.mrtr_server import create_server
from mcp_stateless.server import WorkerHeaderMiddleware

security = RequestStateSecurity(
    keys=[os.environ["MCP_REQUEST_STATE_KEY"]],
    audience="mrtr-provisioning",
)
server = create_server(security)
app = WorkerHeaderMiddleware(server.streamable_http_app())
