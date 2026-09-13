from callcenterfly.artifacts import load_artifact, save_artifact
from callcenterfly.connectome.mock import MockConnectomeBackend
from callcenterfly.data import load_action_catalog, load_decision_points
from callcenterfly.encoding import EncoderConfig, StructuredStimulusEncoder
from callcenterfly.inference import InferenceEngine
from callcenterfly.training import TrainingConfig, train_policy


def test_artifact_round_trip_and_inference(tmp_path, project_root, dataset_root):
    actions = list(load_action_catalog(dataset_root))
    train = load_decision_points(dataset_root, "train")[:80]
    validation = load_decision_points(dataset_root, "validation")[:30]
    encoder = StructuredStimulusEncoder(EncoderConfig(dimension=48, seed=3, text_weight=0.1))
    backend = MockConnectomeBackend(input_dimension=48, readout_dimension=24, seed=4)
    config = TrainingConfig(epochs=1, learning_rate=0.05, settle_steps=2, seed=5)
    policy, _ = train_policy(train, validation, encoder, backend, actions, config)
    save_artifact(
        tmp_path,
        policy,
        {
            "model_name": "test",
            "backend": {
                "type": "mock",
                "name": backend.name,
                "input_dimension": 48,
                "readout_dimension": 24,
                "seed": 4,
                "connectome_used": False,
            },
            "encoder": {"dimension": 48, "seed": 3, "text_weight": 0.1},
            "training": {"seed": 5, "settle_steps": 2},
        },
    )
    loaded, metadata = load_artifact(tmp_path)
    assert loaded.weights.shape == policy.weights.shape
    assert metadata["backend"]["connectome_used"] is False
    engine = InferenceEngine(tmp_path, project_root / "data" / "scripts" / "response_catalog.csv")
    decision = validation[0]
    result = engine.predict(decision)
    assert result.selected_action_family in decision.candidate_actions
    assert result.connectome_used is False
    assert result.response_review_status == "DRAFT_REVIEW_REQUIRED"
