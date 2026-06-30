"""FastAPI app entry point — lifespan, routes, WebSocket."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status

from api.auth import verify_api_key
from api.metrics import get_system_metrics
from api.models import Server, ServerIn, ServerOut
from api.poller import poll_server, run_poll_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_servers: dict[int, Server] = {}
_next_id: int = 1
_poll_task: asyncio.Task | None = None


def _to_out(server: Server) -> ServerOut:
    return ServerOut(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        status=server.status,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background poll loop on startup; cancel it on shutdown."""
    global _poll_task
    _poll_task = asyncio.create_task(run_poll_loop(_servers))
    logger.info("Background poll loop started")
    yield
    if _poll_task is not None:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    logger.info("Background poll loop stopped")


app = FastAPI(title="DevOps Monitoring API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict:
    """Return the current system metrics snapshot."""
    return get_system_metrics()


@app.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    """Stream a metrics JSON frame every second."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(get_system_metrics())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")


@app.post("/servers", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerIn,
    _: Annotated[str, Depends(verify_api_key)],
) -> ServerOut:
    """Register a new monitored server."""
    global _next_id
    server = Server(
        id=_next_id,
        name=payload.name,
        host=payload.host,
        port=payload.port,
        status="unknown",
    )
    _servers[_next_id] = server
    _next_id += 1
    logger.info("Registered server %s (%s)", server.id, server.name)
    return _to_out(server)


@app.get("/servers", response_model=list[ServerOut])
async def list_servers(status: str | None = None) -> list[ServerOut]:
    """List all servers, optionally filtered by status query param ``?status=UP``."""
    servers = list(_servers.values())
    if status is not None:
        servers = [s for s in servers if s.status == status]
    return [_to_out(s) for s in servers]


@app.get("/servers/{server_id}", response_model=ServerOut)
async def get_server(server_id: int) -> ServerOut:
    """Return one server or 404."""
    server = _servers.get(server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _to_out(server)


@app.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    _: Annotated[str, Depends(verify_api_key)],
) -> None:
    """Remove a server or return 404."""
    if server_id not in _servers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    del _servers[server_id]
    logger.info("Deleted server %s", server_id)


@app.post("/servers/{server_id}/check")
async def trigger_check(server_id: int, background_tasks: BackgroundTasks) -> dict:
    """Trigger an immediate background health check for one server."""
    server = _servers.get(server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    background_tasks.add_task(poll_server, server_id, server.base_url(), _servers)
    return {"message": "Health check triggered", "server_id": server_id, "status": server.status}
