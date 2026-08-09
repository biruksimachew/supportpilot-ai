from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_liveness_endpoint() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "supportpilot-api"
    assert payload["environment"] == "local"


def test_readiness_endpoint_when_dependencies_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.health.check_database_readiness",
        lambda: {
            "database": True,
            "pgvector": True,
        },
    )

    response = client.get("/health/ready")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ready"
    assert payload["dependencies"]["database"] is True
    assert payload["dependencies"]["pgvector"] is True


def test_readiness_endpoint_when_database_fails(monkeypatch) -> None:
    def failed_check():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "app.api.routes.health.check_database_readiness",
        failed_check,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503

    payload = response.json()

    assert payload["status"] == "not_ready"
    assert payload["dependencies"]["database"] is False
    assert payload["dependencies"]["pgvector"] is False