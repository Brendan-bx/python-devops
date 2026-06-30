import logging
from fastapi import FastAPI, HTTPException
from models import Server, ServerIn, ServerOut
from health import HealthChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

app = FastAPI(title="DevOps Monitoring API", version="1.0")

_store: dict[int, Server] = {}
_counter = 0
checker = HealthChecker()


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "servers_monitored": len(_store)}


@app.post("/servers", response_model=ServerOut, status_code=201, tags=["Servers"])
async def register_server(server: ServerIn):
    global _counter
    _counter += 1
    record = Server(
        id=_counter,
        name=server.name,
        host=server.host,
        port=server.port,
        tags=server.tags,
    )
    _store[_counter] = record
    return record


@app.get("/servers", response_model=list[ServerOut], tags=["Servers"])
async def list_servers(status: str | None = None):
    servers = list(_store.values())
    if status:
        servers = [s for s in servers if s.status == status]
    return servers


@app.get("/servers/{server_id}", response_model=ServerOut, tags=["Servers"])
async def get_server(server_id: int):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Server not found")
    return _store[server_id]


@app.delete("/servers/{server_id}", status_code=204, tags=["Servers"])
async def delete_server(server_id: int):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Server not found")
    del _store[server_id]


@app.post("/servers/{server_id}/check", response_model=ServerOut, tags=["Servers"])
async def trigger_health_check(server_id: int):
    if server_id not in _store:
        raise HTTPException(status_code=404, detail="Server not found")
    server = await checker.check(_store[server_id])
    return server
