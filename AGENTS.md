# CallCenterFly instructions for Codex agents

## Mission

Build a reproducible research system that tests whether activity from a fixed,
fully retained MaleCNS v1.0 connectome can support selection among approved
credit-union response actions. Keep scientific claims, policy controls, and
software boundaries explicit. This repository is experimental and must never be
presented as a production member-service system.

## Inviolable boundaries

- Keep the connectome, engineered sensory encoder, neural dynamics, trainable
  adapter, action mask, response resolver, and audit layer separate and traceable.
- The real MaleCNS backend must retain every released edge between retained
  neuronal entries under the documented retention policy. Do not crop a convenient
  subcircuit, prune weak or self edges, or replace it with a hidden task policy.
- MaleCNS source weights are immutable. Training may update only an explicitly
  named adapter or separately justified plasticity experiment. Never silently
  describe adapter training as training the connectome.
- The default `mock` backend is for software validation only. Every report and API
  response using it must say `connectome_used: false`; it is not biological evidence.
- Never let raw call state, labels, rewards, or business rules bypass the documented
  stimulus mapping and secretly steer the policy. The action mask may restrict
  eligibility, but must not rank eligible actions.
- Select abstract action families first. Resolve wording afterward from the reviewed
  response catalog. Do not generate free-form financial guidance in the policy loop.
- Response rows marked `DRAFT_REVIEW_REQUIRED` are examples, not approved scripts.
  Never relabel them approved without a recorded operations/compliance/legal review.
- Do not add real calls, member data, credentials, account identifiers, or production
  endpoints. The committed dataset must remain fully synthetic.
- The dataset is CSV/JSONL-first. Do not add XLS or XLSX workbooks.
- Never autonomously move money, modify an account, make authentication decisions,
  promise timing, guarantee reimbursement, or determine legal coverage.
- Preserve negative results, controls, seeds, data hashes, failed gates, and known
  limitations. Weight changes or improved reward alone do not prove fly learning.

## Repository map

- `src/callcenterfly/`: runtime package and command-line interface.
- `data/synthetic/v0.1.0/`: immutable synthetic release and its generator/QA record.
- `data/scripts/`: draft response catalog, separate from learning targets.
- `config/datasets/`: external connectome registries and expected digests.
- `models/mock-baseline-v0/`: small committed software baseline; no connectome.
- `docs/PROJECT_SPECIFICATION.md`: authoritative product/science specification.
- `docs/EXPERIMENT_PROTOCOL.md`: gates, controls, and claim language.
- `media/`: accepted FlyBody/OpenGL visualization PoC; not a neural simulation.
- `scripts/`: data retrieval and smoke-test entry points.
- `tests/`: fast tests that must run without downloading MaleCNS.

## Working rules

1. Read `docs/PROJECT_SPECIFICATION.md` before changing architecture or claims.
2. Do not manually edit generated dataset records. Change the deterministic generator,
   regenerate, run its validator, and review the diff and split-leakage report.
3. Do not download the 1.1 GB graph during ordinary tests or CI. A real graph run must
   be explicitly requested and use the locked registry plus SHA-256 verification.
4. Keep optional neural and serving dependencies out of the core install.
5. Use deterministic seeds and safe, non-pickle artifacts (`npz` plus JSON metadata).
6. Keep raw utterances out of operational audit logs by default.
7. Add or update tests for every behavioral change. At minimum run:

   ```bash
   python -m ruff check .
   python -m pytest
   python scripts/smoke_test.py
   ```

8. Update the README, specification, model card, and experiment protocol whenever the
   shipped behavior or scientific interpretation changes.
9. Preserve third-party attribution and licenses. Large external datasets, papers,
   dependency checkouts, tokens, local paths, and mutable checkpoints stay untracked.
10. Create focused commits. Do not push, publish, or create releases unless the user
    explicitly authorizes that external action.

## Required reporting language

- Say “connectome-derived activity” only when the verified real backend produced it.
- Say “mock readout” for the deterministic software backend.
- Say “action-selection adapter” rather than “fly intelligence.”
- Distinguish training, frozen evaluation, replay, and visualization.
- Passing software tests establishes implementation behavior, not neuroscience validity,
  compliance approval, member safety, or production readiness.
