"""Deterministic software backend used by CI and the committed baseline."""

from __future__ import annotations

import numpy as np

from .base import ConnectomeObservation


class MockConnectomeBackend:
    """Fixed random projection with a bounded settling recurrence.

    This object deliberately does not model biological neural dynamics.
    """

    name = "mock-fixed-projection"
    connectome_used = False

    def __init__(self, input_dimension: int = 128, readout_dimension: int = 64, seed: int = 7):
        self.input_dimension = input_dimension
        self.readout_dimension = readout_dimension
        self.seed = seed
        generator = np.random.default_rng(seed)
        scale = 1.0 / np.sqrt(input_dimension)
        self._projection = generator.normal(
            0.0, scale, size=(readout_dimension, input_dimension)
        ).astype(np.float32)
        self._bias = generator.normal(0.0, 0.04, size=readout_dimension).astype(np.float32)

    def reset(self) -> None:
        return None

    def run(self, stimulus: np.ndarray, settle_steps: int = 6) -> ConnectomeObservation:
        if stimulus.shape != (self.input_dimension,):
            raise ValueError(
                f"expected stimulus shape {(self.input_dimension,)}, got {stimulus.shape}"
            )
        drive = self._projection @ stimulus + self._bias
        state = np.tanh(drive).astype(np.float32)
        steps = max(1, min(int(settle_steps), 64))
        for index in range(1, steps):
            state = np.tanh(0.82 * state + drive / (index + 1.0)).astype(np.float32)
        return ConnectomeObservation(
            readout=state,
            backend=self.name,
            connectome_used=False,
            diagnostics={
                "settle_steps": steps,
                "seed": self.seed,
                "interpretation": "mock readout; not biological evidence",
            },
        )
