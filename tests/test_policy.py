import numpy as np

from callcenterfly.policy import MaskedLinearPolicy


def test_mask_prevents_outside_action():
    policy = MaskedLinearPolicy(["A", "B", "C"], feature_dimension=2)
    policy.bias[:] = [0.0, 0.0, 100.0]
    selection = policy.select(np.ones(2, dtype=np.float32), ["A", "B"])
    assert selection.action in {"A", "B"}
    assert {action for action, _ in selection.probabilities} == {"A", "B"}


def test_full_information_update_increases_preferred_probability():
    policy = MaskedLinearPolicy(["A", "B"], feature_dimension=2)
    features = np.asarray([1.0, 0.5], dtype=np.float32)
    before = float(policy.probabilities(features, ["A", "B"])[0])
    for _ in range(100):
        policy.update_full_information(
            features,
            ["A", "B"],
            {"A": 1.0, "B": -1.0},
            learning_rate=0.05,
        )
    after = float(policy.probabilities(features, ["A", "B"])[0])
    assert after > before
    assert policy.select(features, ["A", "B"]).action == "A"
