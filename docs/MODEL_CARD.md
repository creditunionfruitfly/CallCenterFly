# Model card — `mock-baseline-v0`

## Summary

This committed artifact is a small masked linear adapter trained against a deterministic
fixed random projection. It validates software paths only. It did not load MaleCNS and
must not be described as connectome-derived intelligence.

## Training data

- CallCenterFly Synthetic Credit-Union Calls v0.1.0
- 5,250 train decision points
- 1,125 validation decision points
- Synthetic English templates only
- No scripts and no real member data in model inputs

## Inputs and outputs

The model receives a 64-dimensional mock readout and an eligible action mask. It returns
a probability distribution over the eligible abstract action families. Response wording
is resolved from a separate draft catalog.

## Intended use

- Unit, integration, CLI, service, and artifact-format testing.
- Establishing comparison and reporting code before real-connectome work.

## Held-out software-baseline results

| Metric | Test result |
| --- | ---: |
| Preferred-action accuracy | 91.64% |
| Preferred-or-acceptable rate | 96.80% |
| Mean candidate reward | 0.8973 |
| High-risk preferred-action accuracy | 86.67% |
| Mask violations | 0 / 1,125 |

These high values reflect structured action masks and repetitive synthetic templates.
They are a regression baseline, not a real-connectome result or deployment estimate.

## Prohibited use

- Member servicing, account decisions, authentication, fraud adjudication, compliance
  decisions, financial advice, employee evaluation, or claims about biological learning.

## Limitations

- No connectome was loaded.
- Synthetic templates are simpler than real speech.
- The action masks encode substantial workflow structure.
- The response catalog is unapproved draft wording.
- Aggregate accuracy cannot establish safe performance on high-risk cases.

The authoritative generated metrics are stored beside the artifact and must be reported
with `connectome_used: false`.
