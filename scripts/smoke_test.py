#!/usr/bin/env python3
"""Fast graph-free end-to-end smoke test."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from callcenterfly.artifacts import save_artifact
from callcenterfly.connectome.mock import MockConnectomeBackend
from callcenterfly.data import load_action_catalog, load_decision_points
from callcenterfly.encoding import EncoderConfig, StructuredStimulusEncoder
from callcenterfly.inference import InferenceEngine
from callcenterfly.training import TrainingConfig, train_policy

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    dataset = ROOT / "data" / "synthetic" / "v0.1.0"
    actions = list(load_action_catalog(dataset))
    train = load_decision_points(dataset, "train")[:300]
    validation = load_decision_points(dataset, "validation")[:120]
    encoder_config = EncoderConfig(dimension=64, seed=17, text_weight=0.12)
    encoder = StructuredStimulusEncoder(encoder_config)
    backend = MockConnectomeBackend(input_dimension=64, readout_dimension=32, seed=19)
    config = TrainingConfig(epochs=1, learning_rate=0.05, settle_steps=3, seed=23)
    policy, history = train_policy(train, validation, encoder, backend, actions, config)
    with tempfile.TemporaryDirectory(prefix="callcenterfly-smoke-") as directory:
        model_dir = Path(directory)
        save_artifact(
            model_dir,
            policy,
            {
                "model_name": "temporary-smoke-model",
                "dataset_version": "0.1.0",
                "backend": {
                    "type": "mock",
                    "name": backend.name,
                    "input_dimension": 64,
                    "readout_dimension": 32,
                    "seed": 19,
                    "connectome_used": False,
                },
                "encoder": {"dimension": 64, "seed": 17, "text_weight": 0.12},
                "training": {"seed": 23, "settle_steps": 3},
            },
        )
        engine = InferenceEngine(model_dir, ROOT / "data" / "scripts" / "response_catalog.csv")
        decision = validation[0]
        prediction = engine.predict(decision)
        assert prediction.selected_action_family in decision.candidate_actions
        assert prediction.connectome_used is False
        assert prediction.response_review_status == "DRAFT_REVIEW_REQUIRED"
        print(
            json.dumps(
                {
                    "passed": True,
                    "connectome_used": False,
                    "selected_action": prediction.selected_action_family,
                    "validation_examples": history[-1].validation.examples,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
