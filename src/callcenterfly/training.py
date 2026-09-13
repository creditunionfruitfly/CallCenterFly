"""Contextual-bandit training loop for the small policy adapter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .connectome.base import ConnectomeBackend
from .encoding import StructuredStimulusEncoder
from .evaluation import EvaluationReport, evaluate_policy
from .policy import MaskedLinearPolicy
from .schemas import DecisionPoint


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    epochs: int = 4
    learning_rate: float = 0.04
    l2: float = 1e-5
    settle_steps: int = 6
    seed: int = 20260913


@dataclass(frozen=True, slots=True)
class EpochReport:
    epoch: int
    mean_expected_train_reward: float
    validation: EvaluationReport

    def to_dict(self) -> dict[str, object]:
        return {
            "epoch": self.epoch,
            "mean_expected_train_reward": self.mean_expected_train_reward,
            "validation": self.validation.to_dict(),
        }


def precompute_readouts(
    decisions: list[DecisionPoint],
    encoder: StructuredStimulusEncoder,
    backend: ConnectomeBackend,
    settle_steps: int,
) -> np.ndarray:
    features = np.empty((len(decisions), backend.readout_dimension), dtype=np.float32)
    for index, decision in enumerate(decisions):
        backend.reset()
        features[index] = backend.run(encoder.encode(decision), settle_steps).readout
    return features


def train_policy(
    train_rows: list[DecisionPoint],
    validation_rows: list[DecisionPoint],
    encoder: StructuredStimulusEncoder,
    backend: ConnectomeBackend,
    action_names: list[str],
    config: TrainingConfig,
) -> tuple[MaskedLinearPolicy, list[EpochReport]]:
    policy = MaskedLinearPolicy(action_names, backend.readout_dimension, seed=config.seed)
    train_features = precompute_readouts(train_rows, encoder, backend, config.settle_steps)
    generator = np.random.default_rng(config.seed)
    history: list[EpochReport] = []
    for epoch in range(1, config.epochs + 1):
        expected_reward = 0.0
        for index in generator.permutation(len(train_rows)):
            decision = train_rows[int(index)]
            expected_reward += policy.update_full_information(
                train_features[int(index)],
                decision.candidate_actions,
                decision.candidate_rewards,
                config.learning_rate,
                config.l2,
            )
        validation = evaluate_policy(validation_rows, encoder, backend, policy, config.settle_steps)
        history.append(
            EpochReport(
                epoch=epoch,
                mean_expected_train_reward=expected_reward / max(1, len(train_rows)),
                validation=validation,
            )
        )
    return policy, history
