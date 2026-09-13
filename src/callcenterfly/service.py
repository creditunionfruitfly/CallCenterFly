"""Optional FastAPI boundary for reviewed, abstract action selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import AuditLogger
from .inference import InferenceEngine
from .schemas import DecisionPoint


def create_app(model_dir: Path, response_catalog: Path, audit_path: Path):
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install the serving extras with: pip install -e '.[serve]'") from exc

    engine = InferenceEngine(model_dir, response_catalog)
    audit = AuditLogger(audit_path)
    app = FastAPI(
        title="CallCenterFly experimental API",
        version="0.1.0",
        description="Scripted research boundary; not approved for member servicing.",
    )

    @app.get("/healthz")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "backend": engine.backend.name,
            "connectome_used": engine.backend.connectome_used,
            "production_ready": False,
        }

    @app.post("/v1/decision")
    def decide(payload: dict[str, Any]) -> dict[str, Any]:
        forbidden_targets = {
            "preferred_action_family",
            "acceptable_action_families",
            "acceptable_action_families_json",
            "candidate_rewards",
            "candidate_rewards_json",
        }
        leaked_targets = sorted(forbidden_targets & payload.keys())
        if leaked_targets:
            raise HTTPException(
                status_code=422,
                detail=f"training/evaluation targets are forbidden at inference: {leaked_targets}",
            )
        candidates = payload.get("candidate_actions", payload.get("candidate_actions_json"))
        if not candidates:
            raise HTTPException(status_code=422, detail="candidate_actions is required")
        try:
            decision = DecisionPoint.from_mapping(payload)
            prediction = engine.predict(decision)
        except (TypeError, ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        audit.record(decision, prediction)
        return {
            **prediction.to_dict(),
            "human_review_required": True,
            "production_ready": False,
            "notice": "Draft research output; no account action has been executed.",
        }

    return app
