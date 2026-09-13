"""Inference engine joining encoder, backend, mask, adapter and response resolver."""

from __future__ import annotations

from pathlib import Path

from .artifacts import load_artifact
from .connectome.mock import MockConnectomeBackend
from .encoding import EncoderConfig, StructuredStimulusEncoder
from .responses import ResponseCatalog
from .schemas import DecisionPoint, Prediction, RankedAction


class InferenceEngine:
    def __init__(
        self,
        model_dir: Path,
        response_catalog_path: Path,
    ) -> None:
        self.policy, self.metadata = load_artifact(model_dir)
        backend_meta = self.metadata["backend"]
        if backend_meta["type"] != "mock":
            raise ValueError("baseline inference loader only supports an explicit mock artifact")
        encoder_meta = self.metadata["encoder"]
        self.encoder = StructuredStimulusEncoder(
            EncoderConfig(
                dimension=int(encoder_meta["dimension"]),
                seed=int(encoder_meta["seed"]),
                text_weight=float(encoder_meta["text_weight"]),
            )
        )
        self.backend = MockConnectomeBackend(
            input_dimension=int(backend_meta["input_dimension"]),
            readout_dimension=int(backend_meta["readout_dimension"]),
            seed=int(backend_meta["seed"]),
        )
        self.settle_steps = int(self.metadata["training"]["settle_steps"])
        self.responses = ResponseCatalog.from_csv(response_catalog_path)

    def predict(self, decision: DecisionPoint) -> Prediction:
        self.backend.reset()
        observation = self.backend.run(self.encoder.encode(decision), self.settle_steps)
        selection = self.policy.select(observation.readout, decision.candidate_actions)
        response = self.responses.resolve(selection.action)
        return Prediction(
            decision_id=decision.decision_id,
            selected_action_family=selection.action,
            ranked_actions=tuple(
                RankedAction(action_family=action, probability=probability)
                for action, probability in selection.probabilities
            ),
            backend=observation.backend,
            connectome_used=observation.connectome_used,
            script_id=response.script_id if response else None,
            response_text=response.response_text if response else None,
            response_review_status=response.review_status if response else None,
        )
