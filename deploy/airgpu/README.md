# AirGPU research setup

AirGPU can be used for an interactive Windows/CUDA experiment if the selected image
exposes the GPU to CUDA and the session/disk persist for the full run. Confirm unattended
runtime and billing behavior with the provider before a long experiment.

Baseline setup in PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,serve]"
callcenterfly validate-data --dataset data/synthetic/v0.1.0
python -m pytest
python scripts/smoke_test.py
```

The baseline does not use CUDA. Do not download MaleCNS until the future simulator
backend and checkpoint plan are merged. For that phase, provision at least 32 GB system
RAM, 12 GB GPU memory, adequate persistent disk, and a way to resume headless work.
