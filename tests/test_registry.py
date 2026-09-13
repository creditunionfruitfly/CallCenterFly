import json

from callcenterfly.connectome.registry import verify_registry


def test_malecns_registry_is_locked(project_root, tmp_path):
    path = project_root / "config" / "datasets" / "malecns_v1.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    assert registry["name"] == "MaleCNS v1.0"
    assert registry["license"] == "CC BY 4.0"
    assert registry["files"]["edges.feather"]["bytes"] == 1_051_241_946
    assert len(registry["files"]["edges.feather"]["sha256"]) == 64
    results = verify_registry(path, tmp_path)
    assert len(results) == 3
    assert not any(result.passed for result in results)
