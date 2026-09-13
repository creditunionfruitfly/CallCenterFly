import json

from callcenterfly.audit import AuditLogger
from callcenterfly.data import load_decision_points
from callcenterfly.schemas import Prediction, RankedAction


def test_audit_omits_raw_utterance(tmp_path, dataset_root):
    decision = load_decision_points(dataset_root, "train")[0]
    prediction = Prediction(
        decision_id=decision.decision_id,
        selected_action_family=decision.preferred_action_family,
        ranked_actions=(RankedAction(decision.preferred_action_family, 1.0),),
        backend="mock-fixed-projection",
        connectome_used=False,
        script_id="CCF-DRAFT-001",
        response_text="not logged",
        response_review_status="DRAFT_REVIEW_REQUIRED",
    )
    path = tmp_path / "audit.jsonl"
    AuditLogger(path).record(decision, prediction)
    raw = path.read_text(encoding="utf-8")
    event = json.loads(raw)
    assert decision.member_utterance not in raw
    assert prediction.response_text not in raw
    assert event["raw_utterance_logged"] is False
