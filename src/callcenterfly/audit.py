"""Privacy-minimizing JSONL audit events."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import DecisionPoint, Prediction


class AuditLogger:
    def __init__(self, path: Path):
        self.path = path

    def record(self, decision: DecisionPoint, prediction: Prediction) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "decision_ref": hashlib.sha256(decision.decision_id.encode()).hexdigest()[:16],
            "scenario_id": decision.scenario_id,
            "phase": decision.phase,
            "risk_tier": decision.risk_tier,
            "candidate_actions": list(decision.candidate_actions),
            "selected_action_family": prediction.selected_action_family,
            "script_id": prediction.script_id,
            "script_review_status": prediction.response_review_status,
            "backend": prediction.backend,
            "connectome_used": prediction.connectome_used,
            "raw_utterance_logged": False,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
