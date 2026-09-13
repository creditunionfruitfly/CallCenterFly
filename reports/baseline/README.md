# Baseline report

`mock-baseline-v0` was trained on the v0.1.0 synthetic train split for four epochs with
seed `20260913`. It uses the deterministic fixed random projection, not MaleCNS.

| Metric | Validation | Test |
| --- | ---: | ---: |
| Preferred-action accuracy | 91.73% | 91.64% |
| Preferred-or-acceptable rate | 97.24% | 96.80% |
| Mean candidate reward | 0.9036 | 0.8973 |
| High-risk preferred accuracy | 86.67% | 86.67% |
| Mask-violation rate | 0% | 0% |

Interpretation: the software pipeline can fit the templated synthetic task while obeying
the mask. The result says nothing about MaleCNS representation utility. It must become a
named comparison arm when the real backend is available.
