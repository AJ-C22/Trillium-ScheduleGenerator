import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_frontend_and_health_are_available() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert "Schedule Studio" in response.text


def test_api_solves_and_exports_a_schedule() -> None:
    request = json.loads(Path("examples/basic_schedule.json").read_text())

    solve_response = client.post("/api/solve", json=request)

    assert solve_response.status_code == 200
    result = solve_response.json()
    assert result["report"]["success"] is True
    assert result["report"]["validation_errors"] == []

    export_response = client.post(
        "/api/export/xlsx",
        json={"request": request, "assignments": result["assignments"]},
    )
    assert export_response.status_code == 200
    assert export_response.content.startswith(b"PK")
    assert "spreadsheetml" in export_response.headers["content-type"]
