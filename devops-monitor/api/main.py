"""DevOps Monitoring API — FastAPI application."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status

from api.auth import verify_api_key
from api.metrics import get_system_metrics
from api.models import Server, ServerIn, ServerOut
from api.poller import poll_server, run_poll_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_servers: dict[int, Server] = {}
_next_id = 1
_poll_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background polling loop on startup and cancel it on shutdown."""
    global _poll_task
    _poll_task = asyncio.create_task(run_poll_loop(_servers))
    logger.info("Poll loop started")
    yield
    if _poll_task is not None:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    logger.info("Poll loop stopped")


app = FastAPI(title="DevOps Monitor API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict:
    """Return current system metrics snapshot."""
    return get_system_metrics()


@app.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    """Stream system metrics as JSON frames every second."""
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            payload = get_system_metrics()
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


@app.get("/servers", response_model=list[ServerOut])
async def list_servers() -> list[ServerOut]:
    """List all registered servers with their current status."""
    return [ServerOut.from_server(s) for s in _servers.values()]


@app.post("/servers", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def register_server(
    server_in: ServerIn,
    _key: Annotated[str, Depends(verify_api_key)],
) -> ServerOut:
    """Register a new server to monitor."""
    global _next_id
    server = Server(
        id=_next_id,
        name=server_in.name,
        host=server_in.host,
        port=server_in.port,
        status="UNKNOWN",
    )
    _servers[_next_id] = server
    _next_id += 1
    logger.info("Registered server %s (%s)", server.id, server.name)
    return ServerOut.from_server(server)


@app.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    _key: Annotated[str, Depends(verify_api_key)],
) -> None:
    """Remove a registered server."""
    if server_id not in _servers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    del _servers[server_id]
    logger.info("Deleted server %s", server_id)


@app.post("/servers/{server_id}/check", response_model=ServerOut)
async def check_server(server_id: int) -> ServerOut:
    """Trigger an immediate health check for a server."""
    if server_id not in _servers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    server = _servers[server_id]
    await poll_server(server)
    return ServerOut.from_server(server)
