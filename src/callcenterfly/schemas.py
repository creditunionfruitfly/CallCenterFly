"""Typed boundaries for synthetic decision points and predictions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _json_list(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, (list, tuple)) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("expected a JSON array of strings")
    return tuple(parsed)


def _json_rewards(value: str | Mapping[str, float] | None) -> dict[str, float]:
    if value is None or value == "":
        return {}
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, Mapping):
        raise ValueError("expected a JSON reward object")
    return {str(key): float(reward) for key, reward in parsed.items()}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True, slots=True)
class DecisionPoint:
    """One synthetic call-state observation and its abstract action target."""

    dataset_version: str
    decision_id: str
    call_id: str
    split: str
    turn_index: int
    phase: str
    scenario_id: str
    scenario_family: str
    category: str
    product: str
    intent: str
    member_utterance: str
    valence: str
    arousal: str
    urgency: str
    authentication_state: str
    risk_tier: str
    authorization_claim: str
    status_claim: str
    amount_usd: float | None
    event_age_hours: float | None
    business_day_context: str
    action_mask_group: str
    candidate_actions: tuple[str, ...]
    preferred_action_family: str
    acceptable_action_families: tuple[str, ...]
    prohibited_behaviors: tuple[str, ...]
    candidate_rewards: dict[str, float]

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> DecisionPoint:
        candidate_actions = _json_list(
            row.get("candidate_actions_json", row.get("candidate_actions"))
        )
        preferred = str(row.get("preferred_action_family", ""))
        acceptable = _json_list(
            row.get("acceptable_action_families_json", row.get("acceptable_action_families"))
        )
        rewards = _json_rewards(row.get("candidate_rewards_json", row.get("candidate_rewards")))
        if not rewards and candidate_actions:
            rewards = {
                action: 1.0 if action == preferred else 0.25 if action in acceptable else -1.0
                for action in candidate_actions
            }
        return cls(
            dataset_version=str(row.get("dataset_version", "0.1.0")),
            decision_id=str(row.get("decision_id", "external-request")),
            call_id=str(row.get("call_id", "external-call")),
            split=str(row.get("split", "inference")),
            turn_index=int(row.get("turn_index", 1)),
            phase=str(row.get("phase", "authenticate_and_scope")),
            scenario_id=str(row.get("scenario_id", "UNKNOWN")),
            scenario_family=str(row.get("scenario_family", row.get("intent", "unknown"))),
            category=str(row.get("category", "unknown")),
            product=str(row.get("product", "unknown")),
            intent=str(row.get("intent", row.get("scenario_family", "unknown"))),
            member_utterance=str(row.get("member_utterance", "")),
            valence=str(row.get("valence", "neutral")),
            arousal=str(row.get("arousal", "low")),
            urgency=str(row.get("urgency", "routine")),
            authentication_state=str(row.get("authentication_state", "not_started")),
            risk_tier=str(row.get("risk_tier", "routine")),
            authorization_claim=str(row.get("authorization_claim", "unknown")),
            status_claim=str(row.get("status_claim", "unknown")),
            amount_usd=_optional_float(row.get("amount_usd")),
            event_age_hours=_optional_float(row.get("event_age_hours")),
            business_day_context=str(row.get("business_day_context", "unknown")),
            action_mask_group=str(row.get("action_mask_group", "EXTERNAL")),
            candidate_actions=candidate_actions,
            preferred_action_family=preferred,
            acceptable_action_families=acceptable,
            prohibited_behaviors=_json_list(
                row.get("prohibited_behaviors_json", row.get("prohibited_behaviors"))
            ),
            candidate_rewards=rewards,
        )

    def validate(self, known_actions: set[str] | None = None) -> list[str]:
        issues: list[str] = []
        if not self.candidate_actions:
            issues.append("candidate action mask is empty")
        if self.preferred_action_family not in self.candidate_actions:
            issues.append("preferred action is outside candidate mask")
        if not set(self.acceptable_action_families).issubset(self.candidate_actions):
            issues.append("acceptable action is outside candidate mask")
        if set(self.candidate_rewards) != set(self.candidate_actions):
            issues.append("candidate reward keys do not equal candidate mask")
        if known_actions is not None and not set(self.candidate_actions).issubset(known_actions):
            issues.append("candidate mask includes an unknown action")
        return issues


@dataclass(frozen=True, slots=True)
class RankedAction:
    action_family: str
    probability: float


@dataclass(frozen=True, slots=True)
class Prediction:
    decision_id: str
    selected_action_family: str
    ranked_actions: tuple[RankedAction, ...]
    backend: str
    connectome_used: bool
    script_id: str | None
    response_text: str | None
    response_review_status: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "selected_action_family": self.selected_action_family,
            "ranked_actions": [
                {"action_family": item.action_family, "probability": item.probability}
                for item in self.ranked_actions
            ],
            "backend": self.backend,
            "connectome_used": self.connectome_used,
            "script_id": self.script_id,
            "response_text": self.response_text,
            "response_review_status": self.response_review_status,
        }
