"""Route tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from api.auth import API_KEY
from api import main as main_module
from api.main import app


@pytest.fixture
def client() -> TestClient:
    main_module._servers.clear()
    main_module._next_id = 1
    yield TestClient(app)
    main_module._servers.clear()
    main_module._next_id = 1


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert "cpu_percent" in body


def test_post_servers_without_key_returns_403(client: TestClient) -> None:
    response = client.post(
        "/servers",
        json={"name": "test", "host": "localhost", "port": 8000},
    )
    assert response.status_code == 403


def test_post_servers_with_valid_key(client: TestClient) -> None:
    response = client.post(
        "/servers",
        json={"name": "api-prod", "host": "127.0.0.1", "port": 8080},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "api-prod"
    assert body["status"] == "unknown"
    assert "id" in body

    list_response = client.get("/servers")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_get_server_not_found(client: TestClient) -> None:
    response = client.get("/servers/99999")
    assert response.status_code == 404


def test_delete_server(client: TestClient) -> None:
    create = client.post(
        "/servers",
        json={"name": "to-delete", "host": "127.0.0.1", "port": 9000},
        headers={"X-API-Key": API_KEY},
    )
    server_id = create.json()["id"]

    response = client.delete(f"/servers/{server_id}", headers={"X-API-Key": API_KEY})
    assert response.status_code == 204
    assert client.get(f"/servers/{server_id}").status_code == 404


def test_delete_server_not_found(client: TestClient) -> None:
    response = client.delete("/servers/99999", headers={"X-API-Key": API_KEY})
    assert response.status_code == 404


def test_get_server_by_id(client: TestClient) -> None:
    create = client.post(
        "/servers",
        json={"name": "detail", "host": "127.0.0.1", "port": 8080},
        headers={"X-API-Key": API_KEY},
    )
    server_id = create.json()["id"]
    response = client.get(f"/servers/{server_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "detail"


def test_list_servers_status_filter(client: TestClient) -> None:
    client.post(
        "/servers",
        json={"name": "filtered", "host": "127.0.0.1", "port": 8080},
        headers={"X-API-Key": API_KEY},
    )
    response = client.get("/servers", params={"status": "UP"})
    assert response.status_code == 200
    assert response.json() == []


def test_trigger_check(client: TestClient) -> None:
    create = client.post(
        "/servers",
        json={"name": "check-me", "host": "127.0.0.1", "port": 8000},
        headers={"X-API-Key": API_KEY},
    )
    server_id = create.json()["id"]
    response = client.post(f"/servers/{server_id}/check")
    assert response.status_code == 200
    assert response.json()["server_id"] == server_id


def test_websocket_metrics(client: TestClient) -> None:
    with client.websocket_connect("/ws/metrics") as ws:
        data = ws.receive_json()
        assert "cpu_percent" in data
