from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "FraudShield AI"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_application_info():
    response = client.get("/api/v1/info")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "FraudShield AI"
    assert "Transaction risk scoring" in data["capabilities"]


def test_readiness_endpoint():
    response = client.get("/ready")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["services"]["postgresql"] == "connected"
    assert data["services"]["redis"] == "connected"
