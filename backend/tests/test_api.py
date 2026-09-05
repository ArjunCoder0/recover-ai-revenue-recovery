"""Comprehensive integration tests for the RECOVER FastAPI backend."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mock_mode"] is True
    assert "mock_provider" in data


def test_simulation_state():
    response = client.get("/api/simulation/state")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "smart_recovery_rate" in data["kpis"]
    assert "smart_net_revenue" in data["kpis"]
    assert data["mock_mode"] is True
    assert data["n"] >= 50


def test_run_simulation():
    response = client.post(
        "/api/simulation/run",
        json={"n": 100, "seed": 99, "controls": None, "llm": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["n"] == 100
    assert data["seed"] == 99
    assert data["total_cases"] == 100
    assert data["kpis"]["total_cases"] == 100


def test_get_cases_and_filter():
    response = client.get("/api/cases?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["cases"]) <= 10
    assert data["total"] > 0

    # Filter by failure_class
    response_soft = client.get("/api/cases?failure_class=SOFT")
    assert response_soft.status_code == 200
    soft_data = response_soft.json()
    for c in soft_data["cases"]:
        assert c["failure_class"] == "SOFT"


def test_get_case_detail():
    # Get a valid case ID first
    cases_res = client.get("/api/cases?page=1&page_size=1")
    first_case_id = cases_res.json()["cases"][0]["id"]

    response = client.get(f"/api/cases/{first_case_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["id"] == first_case_id
    assert "why_chosen" in data
    assert "alternatives" in data
    assert len(data["alternatives"]) > 0
    assert "history" in data


def test_decision_intelligence():
    response = client.get("/api/decision-intelligence")
    assert response.status_code == 200
    data = response.json()
    assert "arms" in data
    assert "arms_by_class" in data
    assert len(data["arms"]) > 0
    # Check that arms contain expected fields
    first_arm = data["arms"][0]
    assert "arm" in first_arm
    assert "alpha" in first_arm
    assert "beta" in first_arm
    assert "mean_prob" in first_arm


def test_policy_controls():
    # Fetch current controls
    response = client.get("/api/policy/controls")
    assert response.status_code == 200
    data = response.json()
    assert "controls" in data
    assert "hard_rules" in data
    assert len(data["hard_rules"]) == 8

    # Update controls
    controls = data["controls"]
    controls["max_retries"] = 4
    update_res = client.post("/api/policy/controls", json=controls)
    assert update_res.status_code == 200
    assert update_res.json()["controls"]["max_retries"] == 4


def test_reliability_10_duplicate_blast():
    # Test 10-duplicate blast test
    blast_res = client.post(
        "/api/reliability/blast-test",
        json={"count": 10, "error_code": "INSUFFICIENT_FUNDS", "amount": 1499.0},
    )
    assert blast_res.status_code == 200
    data = blast_res.json()
    assert data["total_bursts"] == 10
    assert data["processed"] == 1
    assert data["blocked"] == 9
    assert data["duplicate_executions"] == 0
    assert data["status"] == "PASS"

    # Check stats
    stats_res = client.get("/api/reliability/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["processed_count"] >= 1
    assert stats["total_duplicates_blocked"] >= 9


def test_simulate_webhook():
    res = client.post(
        "/api/reliability/simulate-webhook",
        json={
            "error_code": "UPI_TIMEOUT",
            "amount": 999.0,
            "method": "upi",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "status" in data


def test_human_review_queue_and_action():
    queue_res = client.get("/api/human-review/queue")
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert isinstance(queue, list)

    if queue:
        target_case_id = queue[0]["case_id"]
        action_res = client.post(
            "/api/human-review/action",
            json={
                "case_id": target_case_id,
                "action": "APPROVE",
                "note": "Approved in automated backend test",
            },
        )
        assert action_res.status_code == 200
        assert action_res.json()["success"] is True


def test_audit_trail_and_export():
    audit_res = client.get("/api/audit-trail?page=1&page_size=20")
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert "logs" in data
    assert "total" in data

    export_res = client.get("/api/audit-trail/export")
    assert export_res.status_code == 200
    assert isinstance(export_res.json(), list)


def test_taxonomy_and_integration_map():
    tax_res = client.get("/api/taxonomy")
    assert tax_res.status_code == 200
    tax = tax_res.json()
    assert "SOFT" in tax["classes"]
    assert "HARD" in tax["classes"]

    imap_res = client.get("/api/integration-map")
    assert imap_res.status_code == 200
    imap = imap_res.json()
    assert "webhook_events" in imap
    assert "api_endpoints" in imap
