"""Small masked policy adapter trained on top of a frozen readout."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class PolicySelection:
    action: str
    probabilities: tuple[tuple[str, float], ...]


class MaskedLinearPolicy:
    """Linear softmax adapter with full-information contextual-bandit updates."""

    def __init__(
        self,
        action_names: Sequence[str],
        feature_dimension: int,
        seed: int = 20260913,
        weights: np.ndarray | None = None,
        bias: np.ndarray | None = None,
    ) -> None:
        if not action_names or len(set(action_names)) != len(action_names):
            raise ValueError("action names must be non-empty and unique")
        self.action_names = tuple(action_names)
        self.feature_dimension = int(feature_dimension)
        self.seed = int(seed)
        self.action_index = {name: index for index, name in enumerate(self.action_names)}
        expected = (len(self.action_names), self.feature_dimension)
        self.weights = (
            np.zeros(expected, dtype=np.float32)
            if weights is None
            else np.asarray(weights, dtype=np.float32).copy()
        )
        self.bias = (
            np.zeros(len(self.action_names), dtype=np.float32)
            if bias is None
            else np.asarray(bias, dtype=np.float32).copy()
        )
        if self.weights.shape != expected or self.bias.shape != (len(self.action_names),):
            raise ValueError("policy parameter shape mismatch")

    def _candidate_indices(self, candidates: Sequence[str]) -> np.ndarray:
        if not candidates:
            raise ValueError("candidate action mask cannot be empty")
        unknown = set(candidates) - self.action_index.keys()
        if unknown:
            raise ValueError(f"unknown candidate actions: {sorted(unknown)}")
        return np.asarray([self.action_index[action] for action in candidates], dtype=np.int64)

    def probabilities(
        self, features: np.ndarray, candidates: Sequence[str], temperature: float = 1.0
    ) -> np.ndarray:
        features = np.asarray(features, dtype=np.float32)
        if features.shape != (self.feature_dimension,):
            raise ValueError(
                f"expected feature shape {(self.feature_dimension,)}, got {features.shape}"
            )
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        indices = self._candidate_indices(candidates)
        logits = (self.weights[indices] @ features + self.bias[indices]) / temperature
        logits -= np.max(logits)
        probabilities = np.exp(logits, dtype=np.float64)
        probabilities /= probabilities.sum()
        return probabilities.astype(np.float32)

    def select(self, features: np.ndarray, candidates: Sequence[str]) -> PolicySelection:
        probabilities = self.probabilities(features, candidates)
        order = np.argsort(-probabilities, kind="stable")
        ranked = tuple((candidates[index], float(probabilities[index])) for index in order)
        return PolicySelection(action=ranked[0][0], probabilities=ranked)

    def update_full_information(
        self,
        features: np.ndarray,
        candidates: Sequence[str],
        rewards: Mapping[str, float],
        learning_rate: float,
        l2: float = 1e-5,
    ) -> float:
        """Maximize expected masked reward when all candidate rewards are known."""

        indices = self._candidate_indices(candidates)
        probabilities = self.probabilities(features, candidates)
        reward_vector = np.asarray(
            [float(rewards[action]) for action in candidates], dtype=np.float32
        )
        expected_reward = float(probabilities @ reward_vector)
        logit_gradient = probabilities * (reward_vector - expected_reward)
        for local_index, action_index in enumerate(indices):
            self.weights[action_index] *= 1.0 - learning_rate * l2
            self.weights[action_index] += (
                learning_rate * logit_gradient[local_index] * features
            ).astype(np.float32)
            self.bias[action_index] += learning_rate * logit_gradient[local_index]
        return expected_reward
