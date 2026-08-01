import os

from mcp.server.mcpserver import RequestStateSecurity

from mcp_stateless.modern.mrtr_server import create_server
from mcp_stateless.worker_pid import WorkerPidMiddleware

security = RequestStateSecurity(
    keys=[os.environ["MCP_REQUEST_STATE_KEY"]],
    audience="mrtr-provisioning",
)
server = create_server(security)
app = WorkerPidMiddleware(server.streamable_http_app())
