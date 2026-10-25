# Documentation guide

The portfolio entry points are [the main README](../README.md), [the case study](CASE_STUDY.md), [the preparation and validation report](PORTFOLIO_RELEASE_REPORT.md), and [the rights review](RIGHTS_REVIEW.md).

The [final QA classification](QA_FINALIZATION.md) explains all 15 initial failures. [RIGHTS.md](../RIGHTS.md) records the owner's decision to retain original code and documentation without a general open-source license; [ASSET_PROVENANCE.json](ASSET_PROVENANCE.json) records the confirmed origin and exact hashes of the reviewed images.

Other reports are historical engineering records. Their dates, assumptions, test totals and open issues belong to their checkpoints. They must not be read as current acceptance or proof that all described features remain active. They are retained to make analysis and iteration inspectable.

Historical reports may link to `artifacts/`, build outputs, source image batches or personal-save manifests. Those files are deliberately excluded from this release candidate. Such references identify evidence locations from the original work; the public checkout does not include them. Workstation usernames were removed from historical paths. Some older audit tools require those unavailable inputs and are not supported fresh-install entry points.

The README and case study use only the eight [owner-supplied application screenshots](images/playtest/), documented in their [capture manifest](images/playtest/captures.json). Earlier synthetic QA captures remain historical test evidence and are not embedded in either presentation. Proposed file changes are listed in [PORTFOLIO_CHANGES.csv](PORTFOLIO_CHANGES.csv). Asset hashes and unresolved provenance are in [ASSET_INVENTORY.csv](ASSET_INVENTORY.csv). Inspected package versions and declared licenses are in [DEPENDENCY_INVENTORY.csv](DEPENDENCY_INVENTORY.csv).
