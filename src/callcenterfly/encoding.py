"""Deterministic structured-to-stimulus mapping.

This is an engineered task interface, not a measured olfactory code.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

import numpy as np

from .schemas import DecisionPoint

TOKEN_PATTERN = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True, slots=True)
class EncoderConfig:
    dimension: int = 128
    seed: int = 20260913
    text_weight: float = 0.16


class StructuredStimulusEncoder:
    """Hash structured call state into a stable bounded stimulus vector."""

    def __init__(self, config: EncoderConfig | None = None) -> None:
        self.config = config or EncoderConfig()
        if self.config.dimension < 32:
            raise ValueError("encoder dimension must be at least 32")

    def _project(self, vector: np.ndarray, token: str, weight: float, copies: int = 3) -> None:
        digest = hashlib.blake2b(f"{self.config.seed}:{token}".encode(), digest_size=16).digest()
        for offset in range(copies):
            start = offset * 4
            index = int.from_bytes(digest[start : start + 4], "little") % self.config.dimension
            sign = 1.0 if digest[12 + offset] & 1 else -1.0
            vector[index] += sign * weight

    def encode(self, decision: DecisionPoint) -> np.ndarray:
        vector = np.zeros(self.config.dimension, dtype=np.float32)
        fields = {
            "phase": decision.phase,
            "scenario": decision.scenario_family,
            "category": decision.category,
            "product": decision.product,
            "intent": decision.intent,
            "valence": decision.valence,
            "arousal": decision.arousal,
            "urgency": decision.urgency,
            "authentication": decision.authentication_state,
            "risk": decision.risk_tier,
            "authorization": decision.authorization_claim,
            "status": decision.status_claim,
            "business_day": decision.business_day_context,
        }
        for name, value in fields.items():
            self._project(vector, f"{name}={value}", 1.0)

        for token in TOKEN_PATTERN.findall(decision.member_utterance.lower())[:80]:
            self._project(vector, f"word={token}", self.config.text_weight, copies=1)

        if decision.amount_usd is not None:
            amount = min(1.0, math.log1p(max(0.0, decision.amount_usd)) / math.log(100_001.0))
            self._project(vector, "numeric=amount", amount, copies=2)
        if decision.event_age_hours is not None:
            age = min(1.0, math.log1p(max(0.0, decision.event_age_hours)) / math.log(8_761.0))
            self._project(vector, "numeric=event_age", age, copies=2)

        norm = float(np.linalg.norm(vector))
        if norm:
            vector /= norm
        gain = 1.0
        gain += {"medium": 0.12, "high": 0.28}.get(decision.arousal, 0.0)
        gain += {"time_sensitive": 0.10, "immediate": 0.24}.get(decision.urgency, 0.0)
        gain += 0.10 if decision.valence == "negative" else 0.0
        return np.clip(vector * gain, -1.5, 1.5).astype(np.float32)
