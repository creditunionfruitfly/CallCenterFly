# Third-party data and media

## MaleCNS v1.0

The MaleCNS collaboration includes FlyEM at HHMI Janelia, the University of Cambridge
Department of Zoology, the MRC Laboratory of Molecular Biology, Google Research, and the
authors/contributors identified by the release.

- Dataset: <https://male-cns.janelia.org/download/>
- Paper: <https://doi.org/10.1016/j.cell.2026.08.015>
- License: CC BY 4.0

The large MaleCNS files are not bundled. `config/datasets/malecns_v1.json` records the
source URLs, byte counts, hashes, and intended retention policy. Future normalized data
and simulation outputs are project transformations, not measurements supplied or
validated by the dataset creators.

## FlyBody visualization model

The concept video uses the FlyBody MuJoCo model from the Turaga Lab / HHMI Janelia and
Google DeepMind collaborators.

- Repository: <https://github.com/TuragaLab/flybody>
- PoC source commit: `d015e9bfe441bd90ae431bac24c55cb74bdbce26`
- Upstream license: Apache License 2.0
- Paper: <https://doi.org/10.1038/s41586-025-09029-4>

Only rendered PoC media is committed here. The video is a visualization and does not
contain or depict a running MaleCNS connectome.

## Synthetic dataset

The CallCenterFly dataset and templates are project-authored, synthetic material covered
by the repository's MIT license. Source registry links ground scenario categories but do
not copy institution scripts or account data. Trademarks such as Zelle identify a
payment-rail scenario and do not imply affiliation or endorsement.
