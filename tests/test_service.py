from fastapi.testclient import TestClient

from callcenterfly.service import create_app


def test_service_is_fail_closed_and_explicit(tmp_path, project_root):
    app = create_app(
        project_root / "models" / "mock-baseline-v0",
        project_root / "data" / "scripts" / "response_catalog.csv",
        tmp_path / "audit.jsonl",
    )
    client = TestClient(app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["connectome_used"] is False
    assert health.json()["production_ready"] is False

    payload = {
        "decision_id": "service-test",
        "phase": "investigate_and_classify",
        "scenario_id": "CU004",
        "scenario_family": "zelle_pending_recipient_unenrolled",
        "category": "p2p_payments",
        "product": "zelle",
        "intent": "zelle_pending_recipient_unenrolled",
        "member_utterance": "My synthetic payment is pending.",
        "valence": "neutral",
        "arousal": "medium",
        "urgency": "time_sensitive",
        "authentication_state": "verified",
        "risk_tier": "routine",
        "candidate_actions": [
            "CHECK_RECIPIENT_ENROLLMENT",
            "CHECK_TRANSACTION_STATUS",
            "DOCUMENT_CASE",
        ],
    }
    response = client.post("/v1/decision", json=payload)
    assert response.status_code == 200
    assert response.json()["selected_action_family"] in payload["candidate_actions"]
    assert response.json()["human_review_required"] is True
    assert response.json()["connectome_used"] is False
    assert (tmp_path / "audit.jsonl").is_file()

    leaked = client.post(
        "/v1/decision",
        json={**payload, "preferred_action_family": "CHECK_RECIPIENT_ENROLLMENT"},
    )
    assert leaked.status_code == 422
