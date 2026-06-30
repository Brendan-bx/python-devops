"""Tests for Server model and poller."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.models import Server
from api.poller import poll_server, run_poll_loop


def test_server_base_url() -> None:
    server = Server(id=1, name="api", host="localhost", port=8000)
    assert server.base_url() == "http://localhost:8000"


@pytest.mark.asyncio
async def test_poll_server_up() -> None:
    store = {1: Server(id=1, name="api", host="localhost", port=8000)}
    mock_response = MagicMock(status_code=200)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(1, "http://localhost:8000", store)

    assert store[1].status == "UP"


@pytest.mark.asyncio
async def test_poll_server_degraded() -> None:
    store = {1: Server(id=1, name="api", host="localhost", port=8000)}
    mock_response = MagicMock(status_code=503)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(1, "http://localhost:8000", store)

    assert store[1].status == "DEGRADED"


@pytest.mark.asyncio
async def test_poll_server_down() -> None:
    store = {1: Server(id=1, name="api", host="localhost", port=8000)}
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(1, "http://localhost:8000", store)

    assert store[1].status == "DOWN"


@pytest.mark.asyncio
async def test_run_poll_loop_calls_poll_server() -> None:
    store = {1: Server(id=1, name="api", host="localhost", port=8000)}

    with patch("api.poller.poll_server", new_callable=AsyncMock) as mock_poll:
        with patch("api.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()
            with pytest.raises(asyncio.CancelledError):
                await run_poll_loop(store, interval=10)

    mock_poll.assert_called_once()
