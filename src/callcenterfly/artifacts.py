"""Safe, inspectable model artifact persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .policy import MaskedLinearPolicy


def save_artifact(output_dir: Path, policy: MaskedLinearPolicy, metadata: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / "adapter.npz",
        weights=policy.weights,
        bias=policy.bias,
        action_names=np.asarray(policy.action_names, dtype="U64"),
        feature_dimension=np.asarray(policy.feature_dimension, dtype=np.int64),
    )
    payload = {
        "artifact_schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        **metadata,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_artifact(model_dir: Path) -> tuple[MaskedLinearPolicy, dict[str, Any]]:
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    with np.load(model_dir / "adapter.npz", allow_pickle=False) as archive:
        action_names = [str(value) for value in archive["action_names"].tolist()]
        feature_dimension = int(archive["feature_dimension"])
        policy = MaskedLinearPolicy(
            action_names=action_names,
            feature_dimension=feature_dimension,
            seed=int(metadata["training"]["seed"]),
            weights=archive["weights"],
            bias=archive["bias"],
        )
    return policy, metadata
