"""Offline metrics for masked action selection."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .connectome.base import ConnectomeBackend
from .encoding import StructuredStimulusEncoder
from .policy import MaskedLinearPolicy
from .schemas import DecisionPoint


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    split: str
    examples: int
    preferred_accuracy: float
    acceptable_or_preferred_rate: float
    mean_reward: float
    mask_violation_rate: float
    high_risk_examples: int
    high_risk_preferred_accuracy: float | None
    backend: str
    connectome_used: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "split": self.split,
            "examples": self.examples,
            "preferred_accuracy": self.preferred_accuracy,
            "acceptable_or_preferred_rate": self.acceptable_or_preferred_rate,
            "mean_reward": self.mean_reward,
            "mask_violation_rate": self.mask_violation_rate,
            "high_risk_examples": self.high_risk_examples,
            "high_risk_preferred_accuracy": self.high_risk_preferred_accuracy,
            "backend": self.backend,
            "connectome_used": self.connectome_used,
        }


def evaluate_policy(
    decisions: Iterable[DecisionPoint],
    encoder: StructuredStimulusEncoder,
    backend: ConnectomeBackend,
    policy: MaskedLinearPolicy,
    settle_steps: int = 6,
) -> EvaluationReport:
    rows = list(decisions)
    preferred = 0
    acceptable = 0
    violations = 0
    reward_total = 0.0
    high_risk_total = 0
    high_risk_preferred = 0
    for decision in rows:
        backend.reset()
        observation = backend.run(encoder.encode(decision), settle_steps)
        selection = policy.select(observation.readout, decision.candidate_actions)
        action = selection.action
        violations += int(action not in decision.candidate_actions)
        is_preferred = action == decision.preferred_action_family
        is_acceptable = is_preferred or action in decision.acceptable_action_families
        preferred += int(is_preferred)
        acceptable += int(is_acceptable)
        reward_total += decision.candidate_rewards.get(action, -1.0)
        if decision.risk_tier == "high":
            high_risk_total += 1
            high_risk_preferred += int(is_preferred)
    count = len(rows)
    split = rows[0].split if rows else "empty"
    return EvaluationReport(
        split=split,
        examples=count,
        preferred_accuracy=preferred / count if count else 0.0,
        acceptable_or_preferred_rate=acceptable / count if count else 0.0,
        mean_reward=reward_total / count if count else 0.0,
        mask_violation_rate=violations / count if count else 0.0,
        high_risk_examples=high_risk_total,
        high_risk_preferred_accuracy=(
            high_risk_preferred / high_risk_total if high_risk_total else None
        ),
        backend=backend.name,
        connectome_used=backend.connectome_used,
    )
