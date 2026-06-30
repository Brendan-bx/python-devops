"""Background health-check logic for monitored servers."""

import asyncio
import logging

import httpx

from api.models import Server

logger = logging.getLogger(__name__)


async def poll_server(server_id: int, url: str, store: dict[int, Server]) -> None:
    """
    GET ``{url}/health`` and update the server status in *store*.

    Status is ``UP`` (200), ``DEGRADED`` (non-200), or ``DOWN`` (connection error).
    """
    server = store.get(server_id)
    if server is None:
        return

    health_url = f"{url.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
        server.status = "UP" if response.status_code == 200 else "DEGRADED"
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        logger.debug("Health check failed for server %s: %s", server_id, exc)
        server.status = "DOWN"


async def run_poll_loop(store: dict[int, Server], interval: int = 10) -> None:
    """Poll every server in *store* concurrently, then sleep *interval* seconds."""
    while True:
        if store:
            tasks = [
                poll_server(sid, server.base_url(), store)
                for sid, server in store.items()
            ]
            await asyncio.gather(*tasks)
        await asyncio.sleep(interval)
