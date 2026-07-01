"""Async health-check polling for registered servers."""

import asyncio
import logging

import httpx

from api.models import Server

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 10
HEALTH_TIMEOUT_SECONDS = 5.0


async def poll_server(server: Server) -> None:
    """
    Probe ``GET /health`` on a server and update its status in place.

    Status values:
        UP       — HTTP 200 with ``{"status": "ok"}``
        DEGRADED — HTTP 200 but unexpected body, or slow response
        DOWN     — connection error or non-2xx response
    """
    url = f"{server.base_url()}/health"
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        if response.status_code == 200:
            body = response.json()
            if body.get("status") == "ok":
                server.status = "UP"
            else:
                server.status = "DEGRADED"
        elif 400 <= response.status_code < 500:
            server.status = "DEGRADED"
        else:
            server.status = "DOWN"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Health check failed for server %s: %s", server.id, exc)
        server.status = "DOWN"


async def run_poll_loop(servers: dict[int, Server]) -> None:
    """
    Continuously poll every registered server every 10 seconds.

    Uses ``asyncio.gather`` to run health checks concurrently.
    """
    while True:
        if servers:
            await asyncio.gather(
                *(poll_server(server) for server in servers.values())
            )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
