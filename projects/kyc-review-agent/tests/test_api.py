from fastapi.testclient import TestClient

from kyc_review_agent.api import app

client = TestClient(app)


def test_health_endpoints_report_ready() -> None:
    assert client.get("/v1/health/live").json() == {"status": "healthy"}
    assert client.get("/v1/health/ready").json() == {"status": "ready"}


def test_review_endpoint_returns_structured_result() -> None:
    response = client.post(
        "/v1/review-tasks",
        headers={"X-Actor-Id": "auditor_zhang"},
        json={
            "case_id": "SYN-KYC-001",
            "review_goal": "Check document completeness",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "more_information_required"
    assert body["missing_materials"] == ["address_proof"]


def test_review_endpoint_rejects_cross_case_access() -> None:
    response = client.post(
        "/v1/review-tasks",
        headers={"X-Actor-Id": "auditor_zhang"},
        json={
            "case_id": "SYN-KYC-002",
            "review_goal": "Check document completeness",
        },
    )

    assert response.status_code == 403
