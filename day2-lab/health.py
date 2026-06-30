import asyncio
import logging
import time
import httpx
from models import Server

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self, timeout: float = 5.0, degraded_threshold_ms: float = 500.0):
        self.timeout = timeout
        self.degraded_threshold_ms = degraded_threshold_ms

    async def check(self, server: Server) -> Server:
        url = f"{server.base_url()}/health"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
            elapsed_ms = (time.time() - start) * 1000
            if resp.status_code == 200 and elapsed_ms <= self.degraded_threshold_ms:
                server.status = "UP"
            elif resp.status_code == 200:
                server.status = "DEGRADED"
            else:
                server.status = "DEGRADED"
            logger.info("%-20s %s  (%.0f ms)", server.name, server.status, elapsed_ms)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            server.status = "DOWN"
            logger.warning("%-20s DOWN — %s", server.name, e)
        return server

    async def check_all(self, servers: list[Server]) -> list[Server]:
        return await asyncio.gather(*[self.check(s) for s in servers])
