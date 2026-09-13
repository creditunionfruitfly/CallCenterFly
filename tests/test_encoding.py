import numpy as np

from callcenterfly.data import load_decision_points
from callcenterfly.encoding import EncoderConfig, StructuredStimulusEncoder


def test_encoder_is_deterministic_and_bounded(dataset_root):
    decision = load_decision_points(dataset_root, "train")[0]
    encoder = StructuredStimulusEncoder(EncoderConfig(dimension=64, seed=42))
    first = encoder.encode(decision)
    second = encoder.encode(decision)
    assert first.shape == (64,)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    assert np.max(np.abs(first)) <= 1.5


def test_encoder_distinguishes_decisions(dataset_root):
    first, second = load_decision_points(dataset_root, "train")[:2]
    encoder = StructuredStimulusEncoder(EncoderConfig(dimension=64, seed=42))
    assert not np.array_equal(encoder.encode(first), encoder.encode(second))
