"""Explicit placeholder for the future full MaleCNS simulator adapter."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .base import BackendUnavailable, ConnectomeObservation


class MaleCNSBackend:
    """Contract placeholder; no real simulator is shipped in the baseline commit."""

    name = "malecns-v1-full-graph"
    connectome_used = True

    def __init__(self, data_dir: Path, input_dimension: int = 128, readout_dimension: int = 64):
        self.data_dir = Path(data_dir)
        self.input_dimension = input_dimension
        self.readout_dimension = readout_dimension
        raise BackendUnavailable(
            "MaleCNS data verification exists, but the full-graph simulation kernel is not "
            "integrated in baseline v0.1. Use backend=mock for software validation."
        )

    def reset(self) -> None:
        raise BackendUnavailable("MaleCNS backend is not integrated")

    def run(self, stimulus: np.ndarray, settle_steps: int) -> ConnectomeObservation:
        del stimulus, settle_steps
        raise BackendUnavailable("MaleCNS backend is not integrated")
