# CallCenterFly Synthetic Credit-Union Calls v0.1.0

## Purpose

This is the first dataset layer for the CallCenterFly experiment: a deterministic,
fully synthetic set of member call situations and abstract response objectives for a
frozen-connectome-plus-trainable-readout system.

It contains **no customer-service scripts and no fly-response wording**. The next
project phase can map the stable action families in `action_catalog.csv` to separately
reviewed, institution-specific scripts.

## Contents

- CSV-first release; no spreadsheet workbook is included.
- 25 balanced scenario families.
- 2,500 three-decision call episodes.
- 7,500 flattened decision points.
- Fixed split: 1,750 train / 375 validation / 375 test episodes.
- JSONL episode files and CSV decision files.
- Scenario, action, prohibited-behavior, source, schema, and QA artifacts.

## Synthetic-data rules

- Every utterance is generated from project-authored templates and synthetic facts.
- No real call recording, transcript, member name, employee name, institution name,
  account number, card number, phone number, email, street address, SSN, or credentials
  are used.
- Dollar values and event ages are random synthetic variables and must not be treated
  as institution policy.
- `Zelle` is used only as a payment-rail scenario label. No Zelle or credit-union
  service promise is inferred.

## Intended learning task

At each decision point, the model observes structured call state plus one synthetic
member utterance. It selects one action from `candidate_actions_json`. The frozen
connectome may supply a state embedding; a small trainable readout or contextual bandit
selects the abstract action family. A compliance mask removes actions that are not
eligible for that context.

Reward defaults:

- Preferred action: `+1.00`
- Acceptable action: `+0.25`
- Other mask-eligible action: `-1.00`
- Prohibited behavior: `-3.00` and never presented as an eligible production action

## Important limitations

- This is a research dataset, not legal advice, operating procedure, or production QA.
- Potential Regulation E, Regulation Z, or Regulation CC flags require institution and
  counsel review; they are not final legal determinations.
- Institution-specific authentication, disclosures, holds, limits, fees, SLAs,
  escalation ownership, and complaint handling are intentionally not encoded as facts.
- The templates are English-only and do not yet model ASR noise, accents, multilingual
  calls, accessibility needs, vulnerable-adult handling, deceased-member servicing,
  bankruptcy, subpoenas, or complex commercial accounts.
- Before any real deployment, validate with credit-union operations, compliance, legal,
  information security, fair-lending, accessibility, and model-risk owners.

## Reproduction

Run:

```bash
python3 source/generate_dataset.py
```

The generator uses seed `20260912`. The release date is `2026-09-12`.
