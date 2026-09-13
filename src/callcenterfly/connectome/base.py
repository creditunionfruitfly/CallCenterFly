"""Backend protocol shared by mock and future MaleCNS simulators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


class BackendUnavailable(RuntimeError):
    """Raised when a requested neural backend is not installed or integrated."""


@dataclass(frozen=True, slots=True)
class ConnectomeObservation:
    readout: np.ndarray
    backend: str
    connectome_used: bool
    diagnostics: dict[str, Any]


class ConnectomeBackend(Protocol):
    name: str
    input_dimension: int
    readout_dimension: int
    connectome_used: bool

    def reset(self) -> None:
        """Reset transient neural state without changing fixed weights."""

    def run(self, stimulus: np.ndarray, settle_steps: int) -> ConnectomeObservation:
        """Map one stimulus through a fixed backend and return the readout."""
