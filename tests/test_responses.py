from callcenterfly.data import load_action_catalog
from callcenterfly.responses import ResponseCatalog


def test_every_action_has_a_review_gated_response(project_root, dataset_root):
    catalog = ResponseCatalog.from_csv(project_root / "data" / "scripts" / "response_catalog.csv")
    actions = set(load_action_catalog(dataset_root))
    assert catalog.action_families == actions
    for action in actions:
        response = catalog.resolve(action)
        assert response is not None
        assert response.review_status == "DRAFT_REVIEW_REQUIRED"
