from callcenterfly.data import load_action_catalog, load_decision_points, validate_release


def test_release_contract(dataset_root):
    report = validate_release(dataset_root)
    assert report.passed, report.issues[:5]
    assert report.episode_count == 2500
    assert report.decision_count == 7500
    assert report.action_count == 26


def test_split_sizes_and_action_masks(dataset_root):
    assert len(load_decision_points(dataset_root, "train")) == 5250
    assert len(load_decision_points(dataset_root, "validation")) == 1125
    assert len(load_decision_points(dataset_root, "test")) == 1125
    actions = set(load_action_catalog(dataset_root))
    for decision in load_decision_points(dataset_root, "test")[:100]:
        assert decision.preferred_action_family in decision.candidate_actions
        assert set(decision.acceptable_action_families).issubset(decision.candidate_actions)
        assert set(decision.candidate_actions).issubset(actions)
