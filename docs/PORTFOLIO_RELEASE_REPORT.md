# Portfolio finalization and validation report

Review date: 25 October 2026. **Technical QA passed; portfolio published. The owner explicitly approved the final integration into the default `main` branch. Repository visibility is unchanged.**

## Repository and release basis

| Item | Verified state |
| --- | --- |
| Existing repository | [oezay-kocak/industriova](https://github.com/oezay-kocak/industriova) |
| Fetch and push remote | `origin`, same repository URL |
| Portfolio source branch | `codex/industriova-portfolio-finalization` |
| Published default branch | `main`, tracking `origin/main` |
| Original source baseline | `0e4a9e0c7f80d74916bfeeae39a150374e2d8ebd` |
| Included README polish | `97b51659447c855eaf3f3476515cadbe7b89b686` |
| Existing historical tag | `v0.1.0-alpha`, pointing to `8b4159dbe311571150da9dcfe2f25f75d3a4e55a` |

No repository was created or renamed by the portfolio integration. Remote refs were rechecked before the authorized main update. The original source portfolio was published as `aafff3f` and merged into `main` as `f465276`; README polish `97b5165` is included in the final main integration. No release tag, executable upload or visibility mutation was made. The application source and the complete passing regression results below are unchanged by the final presentation-only integration.

The existing local work substantially exceeds the 94-file committed baseline. It is included so the proposed repository update contains the application source, tests, data and artwork, not just presentation documents. This does not imply that the finalization authored all those development changes. [PORTFOLIO_CHANGES.csv](PORTFOLIO_CHANGES.csv) distinguishes the preserved work from portfolio preparation relative to the baseline at review time.

The application identifies as `0.3.0.contract-auto-test`, package metadata as `0.3.0.dev1`, and opt-in performance mode uses its own version and save directory. The legacy module `__version__` still reads `0.1.0`. Version consolidation remains a release-process follow-up; this task did not change gameplay or save compatibility to hide that discrepancy.

## Final technical results

Environment: Windows, Python 3.12.14, PySide6 6.11.1, pytest 9.1.1; Qt offscreen. Every current `test_*.py` module ran in a fresh process, using three workers and a 180-second timeout per module.

| Measure | Final result |
| --- | --- |
| Modules | 121 / 121 successful |
| Test cases | 3,784 |
| Passed | 3,784 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |

The earlier portfolio pass found 15 reproducible failures. All were investigated: **two implementation defects and 13 obsolete tests or fixtures**. [QA_FINALIZATION.md](QA_FINALIZATION.md) records each original case, the applicable rule and the retained assertions.

Implementation corrections:

- Research tracing now wraps the current feed presentation method instead of a removed ticker method. Opt-in diagnostic startup and heartbeat-stall detection work again.
- Header inter-module spacing was reduced from 10px to 8px. The supported 1366px window no longer expands to 1369px with the tested Windows fonts; all controls remain present.

Test corrections align with existing rules: visible-only runtime refresh, all primary resources initially unlocked, 100-unit downstream prerequisites, the current two-preview recipe ordering, in-bounds resource-overlay persistence with overflow clamping, five visible production lines, fixed-window event aggregation, separate RP/Research event types and retention of small positive XP. No input cases were discarded, tests disabled or gameplay rules changed.

Full results, individual logs and JUnit reports are retained locally under `artifacts/portfolio-finalization/tests/`. The script's final process exit code is not sufficient by itself; all module exits and JUnit totals were checked. Intermediate focused attempts affected by unavailable default temporary directories or old parameter node IDs were not counted as final verification.

## Installation and screenshots

A fresh wheel was built from the final application source and installed to a separate local target using the already available dependency environment. Archive inspection confirmed **370 application assets and all five JSON catalogs**, with no databases, logs, private keys or environment files. The installed entry point started and shut down successfully with isolated application-data directories **and opt-in Research diagnostics enabled**. The import location was checked against the separate installation. No executable was distributed.

This checks local package creation and installation/startup. It is not a clean online dependency download, a packaged Windows acceptance test or cross-platform certification.

The three portfolio screenshots were regenerated after the UI correction, visually reviewed and recorded in [captures.json](images/captures.json). They are actual 1600 × 980 offscreen application renders from a synthetic company, without a save store. Their exact hashes are in the provenance record. The Factory image retains visible power constraints instead of concealing real application behavior.

## Asset provenance and publication eligibility

The owner explicitly confirmed on 25 October 2026 that **all game artwork was created with GPT and no external templates were used**. [ASSET_PROVENANCE.json](ASSET_PROVENANCE.json) binds this declaration to the exact reviewed SHA-256 hashes of **370 application images and three screenshots**. All 373 reviewed files are eligible for the owner's project publication on that recorded basis. This is not a general asset license for repository visitors.

Technical records were also inspected:

- Four integration manifests account for all 353 resource images.
- 164 historical digest comparisons match their current target files; the atlas's source hashes independently match all 353 current resource images.
- Machine/energy integration reports, freight byte-identity reports and Research mask evidence provide additional processing provenance.
- One older Harvester source digest belongs to a superseded opaque image. The current transparent revision is separately identified by later visual evidence and the primary-card tests; it is not mislabeled as byte-identical to that old source.
- All portfolio screenshots are derived from the reviewed application artwork and synthetic state.

The creator declaration is distinct from an independently retrieved generation receipt for each file. Individual prompts/receipts were not available for every image, and no exclusive copyright guarantee is asserted. The provider terms and scope are documented in [RIGHTS_REVIEW.md](RIGHTS_REVIEW.md). No unresolved foreign-template exception was identified after the owner's clarification.

The audit marks missing or changed image hashes as pending; those files must not enter a publication commit without renewed review. The final candidate has no uncleared image entries. Original source images, private evidence exports and generation-session directories are not included.

## Rights decision and third parties

Per the owner's instruction, original code and documentation remain **without a general open-source license**. The earlier MIT proposal is not adopted. No MIT license, general reuse grant or package license declaration was added. [RIGHTS.md](../RIGHTS.md) distinguishes source, documentation, artwork, statutory/platform permissions and third-party components.

[DEPENDENCY_INVENTORY.csv](DEPENDENCY_INVENTORY.csv) records 16 installed runtime/build/development packages including transitive dependencies. Third-party licenses remain applicable; nothing is relabeled as project-owned material. A future executable release requires its own bundled-library and notice review, particularly for Qt/PySide and incorporated runtime components.

## Privacy, preservation and proposed changes

The candidate is checked for recognizable private-key/service-token formats, credential assignments, personal workstation paths, email patterns, broken portfolio links, Python syntax errors and oversized files. Existing reachable textual Git blobs are checked too. The review is heuristic, not a vulnerability or security certification. Git author identity matches the historical repository author and uses a GitHub no-reply address.

Personal workstation paths previously found in 19 documents/helper scripts were sanitized. `.gitignore` excludes personal saves and database formats, credentials, local environments, diagnostics, backup archives, build directories and wheels. Screenshots and package startup do not load personal saves. Build/test outputs and raw asset evidence remain local under ignored `artifacts/`.

Before the first portfolio pass, candidate contents were backed up under `artifacts/portfolio-release/`. Before finalization, a fresh source archive and SHA-256 baseline were saved under `artifacts/portfolio-finalization/`. Neither is part of the commit.

Finalization corrects behavior in two runtime UI/diagnostic files and aligns six existing test modules; it adds no gameplay feature. Incidental whitespace and newline cleanup in other files was checked for identical Python ASTs; historical Markdown hard breaks use explicit backslashes, with the one embedded report-template exception documented in `.gitattributes`. This formatting does not alter the executed Python semantics of the passing suite. Existing development work is retained. The prior deletion of `tests/test_mk_upgrades.py` predates the portfolio work and remains explicitly visible in the complete change list; no test deletion was introduced by this finalization. Legacy package/environment identifiers remain compatible. The duplicate untracked `ProductionZero.spec` is excluded. The index check identified that the root generated economy stress JSON was already tracked: it is explicitly removed from the proposed tree while its local file and Git history are retained; an ignore rule alone would not have excluded it.

The local review commit groups the preserved Industriova source, complete relevant assets/data/tests and the final documentation/QA corrections. [COMMIT_PLAN.md](COMMIT_PLAN.md) gives the review scope and intended message. The committed change inventory is a preparation snapshot against the original baseline, not a prediction that the worktree should stay modified after commit.

## Remaining limits and required approval

Native Windows drag-and-drop, subjective responsiveness, broader DPI/OS combinations and extended human balancing acceptance remain outside this offscreen regression. Local Consortium/leaderboard services are not proof of deployed multiplayer. Version metadata and older build recipes still need consolidation for a future product release. These limits are recorded in the README and case study.

The owner explicitly authorized the regular merge and push of the verified portfolio changes into `main`. No publication approval remains pending for this portfolio version. No visibility change is included; such a change would require separate explicit authorization. No new license decision is needed to retain the current unlicensed-source position. New assets, third-party exceptions or executable bundles need their own review before inclusion.
