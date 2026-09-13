# CallCenterFly experiment protocol

This protocol defines what must be measured before a real MaleCNS run can support any
claim beyond software feasibility. It is intentionally stricter than the mock baseline.

## Modes

| Mode | Mutable component | Meaning |
| --- | --- | --- |
| Mock training | Linear adapter only | Software pipeline test; no connectome evidence |
| Real training | Linear adapter only | Adapter learns from frozen connectome-derived readouts |
| Frozen evaluation | Nothing | Held-out measurement after model selection |
| Replay | Nothing | Deterministic visualization of recorded outputs |
| Plasticity experiment | Named neural efficacies plus adapter, if preregistered | Separate future hypothesis; not baseline |

Every log, dashboard, artifact, and public description must identify the active mode.

## Required controls

1. **Action-prior baseline:** candidate-mask argmax by training-set action frequency.
2. **Lookup baseline:** phase/scenario table fitted only on training data.
3. **Structured linear baseline:** same adapter using declared structured features.
4. **Mock-feature baseline:** same adapter using the seeded random backend.
5. **Phase-only baseline:** removes utterance and scenario identity.
6. **Shuffled-label control:** preserves inputs and masks while permuting targets in
   split-safe fashion.
7. **Permuted-stimulus control:** preserves vector magnitudes but permutes input codes.
8. **No-propagation control:** readout before graph propagation.
9. **Disconnected-graph control:** removes causal paths from input to readout.
10. **Readout permutation:** preserves dimensionality and marginal distribution while
    breaking cell identity.

Adapter capacity, splits, optimizer budget, masks, and evaluation code must be identical
where comparisons permit.

## Gates

### G0 — provenance

- All external files match the locked byte counts and SHA-256 values.
- Normalization is deterministic and produces a recorded graph hash.
- Retained/excluded node and edge counts reconcile to source data.

### G1 — numerical correctness

- Reference microcircuits match an independent implementation within declared tolerance.
- CPU and GPU implementations match on fixed stimuli.
- Batched and unbatched execution agree.
- Reset and checkpoint continuation are deterministic.

### G2 — source-weight immutability

- Source graph weights hash identically before and after adapter training.
- No optimizer owns or receives references to source-weight buffers.
- Checkpoints distinguish source graph, transient state, and adapter parameters.

### G3 — input/readout causality

- Declared stimulation changes declared neural activity versus null input.
- Disconnecting documented paths abolishes or materially reduces the effect.
- Call labels, rewards, and task telemetry do not reach the backend through hidden paths.

### G4 — software safety

- Zero out-of-mask actions across all runs.
- Unknown/empty masks fail closed.
- High-risk scenarios never select unapproved low-risk-only actions.
- Audit records are complete without raw-utterance logging.

### G5 — held-out utility

- Model selection uses validation only.
- Final test evaluation is run once per preregistered candidate.
- Multiple seeds and confidence intervals are reported.
- Real-connectome features exceed the strongest matched control by a preregistered,
  practically meaningful margin.
- Per-scenario and high-risk results do not conceal severe subgroup failures.

### G6 — interpretation

- Negative and null results are retained.
- A changed adapter is not described as changed connectome wiring.
- Passing G0–G5 is described as task utility in a simulation, not sentience, human-like
  understanding, or validated customer-service competence.

## Baseline reward

For candidate action \(a\):

- preferred: `+1.00`
- acceptable: `+0.25`
- other eligible: `-1.00`
- prohibited behavior: `-3.00`, excluded from eligible action space

No account balance, member outcome, employee performance measure, or monetary target is
used as reward in baseline experiments.

## Reporting template

Each run report must include:

- hypothesis and preregistration reference;
- source/data/code hashes and dirty state;
- backend, graph counts, encoder mapping, and readout IDs;
- trainable parameters and frozen parameters;
- seeds, hardware, runtime, and numerical mode;
- split counts and leakage checks;
- metrics with uncertainty;
- every control and ablation result;
- gate pass/fail table;
- deviations and failures; and
- a plain-language limitations statement.

## Stop conditions

Stop rather than reinterpret the run if any source hash fails, graph counts drift,
source weights change unexpectedly, labels leak into inference, mask violations occur,
checkpoints cannot reproduce state, or a comparison was selected after viewing test
results.
