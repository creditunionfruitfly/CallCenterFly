import numpy as np
import pytest

from callcenterfly.connectome.base import BackendUnavailable
from callcenterfly.connectome.malecns import MaleCNSBackend
from callcenterfly.connectome.mock import MockConnectomeBackend


def test_mock_backend_is_fixed_and_explicit():
    backend = MockConnectomeBackend(input_dimension=32, readout_dimension=12, seed=5)
    stimulus = np.linspace(-1, 1, 32, dtype=np.float32)
    first = backend.run(stimulus, 4)
    second = backend.run(stimulus, 4)
    assert np.array_equal(first.readout, second.readout)
    assert first.readout.shape == (12,)
    assert first.connectome_used is False
    assert "mock" in first.backend


def test_real_backend_fails_closed_until_implemented(tmp_path):
    with pytest.raises(BackendUnavailable, match="not integrated"):
        MaleCNSBackend(tmp_path)
