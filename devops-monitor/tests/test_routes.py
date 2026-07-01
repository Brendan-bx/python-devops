"""Tests for API routes and authentication."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api import main
from api.models import Server


@pytest.fixture(autouse=True)
def reset_servers():
    """Clear in-memory server store between tests."""
    main._servers.clear()
    main._next_id = 1
    yield
    main._servers.clear()
    main._next_id = 1


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(main.app)


@pytest.fixture
def auth_headers():
    """Valid API key headers."""
    return {"X-API-Key": "test-secret-key"}


def test_health_returns_ok(client):
    """GET /health must return status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_returns_percentages(client):
    """GET /metrics must expose CPU, memory and disk percentages."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    for key in ("cpu_percent", "memory_percent", "disk_percent"):
        assert 0 <= data[key] <= 100


def test_post_servers_without_api_key_returns_403(client):
    """POST /servers without X-API-Key must be rejected."""
    response = client.post(
        "/servers",
        json={"name": "web", "host": "10.0.0.1", "port": 8080},
    )
    assert response.status_code == 403


def test_post_servers_with_invalid_key_returns_403(client):
    """POST /servers with wrong key must be rejected."""
    response = client.post(
        "/servers",
        json={"name": "web", "host": "10.0.0.1", "port": 8080},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_post_servers_creates_server(client, auth_headers):
    """POST /servers with valid key must return 201."""
    response = client.post(
        "/servers",
        json={"name": "api-prod", "host": "10.0.0.5", "port": 8000},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "api-prod"
    assert data["host"] == "10.0.0.5"
    assert data["port"] == 8000
    assert data["status"] == "UNKNOWN"
    assert "id" in data


def test_get_servers_lists_registered(client, auth_headers):
    """GET /servers must list servers with their status."""
    client.post(
        "/servers",
        json={"name": "db", "host": "10.0.0.2", "port": 5432},
        headers=auth_headers,
    )
    response = client.get("/servers")
    assert response.status_code == 200
    servers = response.json()
    assert len(servers) == 1
    assert servers[0]["name"] == "db"
    assert servers[0]["status"] == "UNKNOWN"


def test_delete_server_not_found_returns_404(client, auth_headers):
    """DELETE /servers/{id} for unknown id must return 404."""
    response = client.delete("/servers/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_server_success(client, auth_headers):
    """DELETE /servers/{id} must remove the server."""
    create = client.post(
        "/servers",
        json={"name": "tmp", "host": "127.0.0.1", "port": 9000},
        headers=auth_headers,
    )
    server_id = create.json()["id"]
    response = client.delete(f"/servers/{server_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/servers").json() == []


def test_check_server_not_found(client):
    """POST /servers/{id}/check for unknown id must return 404."""
    response = client.post("/servers/42/check")
    assert response.status_code == 404


def test_check_server_updates_status(client, auth_headers):
    """Manual health check must update server status."""
    create = client.post(
        "/servers",
        json={"name": "self", "host": "127.0.0.1", "port": 8000},
        headers=auth_headers,
    )
    server_id = create.json()["id"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.poller.httpx.AsyncClient", return_value=mock_client):
        response = client.post(f"/servers/{server_id}/check")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_ws_metrics_sends_json_frame(client):
    """WebSocket /ws/metrics must push a JSON frame with metrics."""
    with client.websocket_connect("/ws/metrics") as websocket:
        data = websocket.receive_json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_percent" in data


def test_server_base_url():
    """Server.base_url must build correct HTTP URL."""
    server = Server(id=1, name="test", host="192.168.1.1", port=8080)
    assert server.base_url() == "http://192.168.1.1:8080"


def test_post_servers_invalid_port(client, auth_headers):
    """POST /servers with invalid port must return 422."""
    response = client.post(
        "/servers",
        json={"name": "bad", "host": "10.0.0.1", "port": 70000},
        headers=auth_headers,
    )
    assert response.status_code == 422
