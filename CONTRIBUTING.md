# Contributing

Read `AGENTS.md`, the project specification, and the experiment protocol before changing
code or claims.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,serve]'
python -m ruff check .
python -m pytest
python scripts/smoke_test.py
```

Pull requests must identify whether they change data, stimulus mapping, neural dynamics,
readout, trainable parameters, action masks, scripts, or reporting. Include deterministic
tests and preserve negative results. Do not add real member data, XLS/XLSX files, large
MaleCNS inputs, generated checkpoints, or credentials.
