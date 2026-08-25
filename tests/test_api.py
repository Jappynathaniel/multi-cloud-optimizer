import os
from uuid import uuid4
os.environ["REDBRIDGE_DATABASE_URL"] = "sqlite:///./test_redbridge.db"
os.environ["REDBRIDGE_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_connection_secret_not_returned():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/v1/connections", json={"name": f"test-aws-{uuid4()}", "provider": "aws", "config": {"role_arn": "arn:example"}})
        assert response.status_code == 201
        assert "role_arn" not in response.text


def test_agent_is_disabled_without_key():
    with TestClient(app) as client:
        response = client.post("/v1/recommendations/999/agent-explanation", json={"question": "Explain"})
        assert response.status_code == 404


def test_capacity_scenario_is_explicit_about_assumptions():
    with TestClient(app) as client:
        response = client.post("/v1/scenarios/capacity", json={"current_monthly_cost": 100,
            "traffic_change_percent": 25, "current_utilization_percent": 50})
        assert response.status_code == 200
        assert response.json()["mode"] == "deterministic_scenario"
        assert response.json()["projected_monthly_cost"] == 96.15

