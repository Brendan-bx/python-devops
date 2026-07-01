"""Tests for the async server poller."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.models import Server
from api.poller import poll_server


@pytest.mark.asyncio
async def test_poll_server_sets_up_on_ok():
    """Server status must be UP when health returns ok."""
    server = Server(id=1, name="api", host="10.0.0.1", port=8000)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(server)

    assert server.status == "UP"


@pytest.mark.asyncio
async def test_poll_server_sets_degraded_on_wrong_body():
    """Server status must be DEGRADED when body is unexpected."""
    server = Server(id=2, name="api", host="10.0.0.2", port=8000)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "degraded"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(server)

    assert server.status == "DEGRADED"


@pytest.mark.asyncio
async def test_poll_server_sets_down_on_connection_error():
    """Server status must be DOWN when the health check fails."""
    server = Server(id=3, name="api", host="10.0.0.3", port=8000)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(server)

    assert server.status == "DOWN"


@pytest.mark.asyncio
async def test_poll_server_sets_down_on_server_error():
    """Server status must be DOWN on HTTP 5xx responses."""
    server = Server(id=4, name="api", host="10.0.0.4", port=8000)

    mock_response = MagicMock()
    mock_response.status_code = 503

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        await poll_server(server)

    assert server.status == "DOWN"
