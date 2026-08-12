from fastapi.testclient import TestClient

from minici.web.app import create_app


def test_dashboard_and_api(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    page = client.get("/")
    assert page.status_code == 200
    assert "MiniCI Dashboard" in page.text
    runs = client.get("/api/runs")
    assert runs.status_code == 200
    assert runs.json() == []
    assert client.get("/api/runs?limit=0").status_code == 400
    assert client.get("/api/runs/999").status_code == 404
    assert client.get("/api/runs/999/logs").status_code == 404
    assert client.post("/api/run").status_code == 409
    assert client.post("/api/cancel").json()["status"] == "cancellation requested"
