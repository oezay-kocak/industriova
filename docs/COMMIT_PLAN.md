# Local portfolio commit

Branch: `codex/industriova-portfolio-finalization`.

Base: `0e4a9e0c7f80d74916bfeeae39a150374e2d8ebd` from the existing `origin/main`.

Intended subject: **Prepare Industriova portfolio source and complete technical QA**

The commit brings the existing uncommitted Industriova application into the existing repository, including source, JSON data, reviewed artwork, tests, historical engineering records and build/QA helpers. It also includes the two finalization defect fixes, six updated test modules, current portfolio documentation, rights/provenance records and ignore rules.

The broad source update is preserved pre-existing development, not newly developed gameplay in the portfolio task. The complete [change inventory](PORTFOLIO_CHANGES.csv) identifies each path and its preparation status. It exposes the pre-existing legacy MK test deletion rather than silently hiding it.

Validation: 3,784 passed across 121 modules, zero failures/errors/skips; separate final wheel installation and diagnostics-enabled application startup/shutdown; three refreshed synthetic screenshots; image hashes and publication eligibility checked; syntax, entry links, whitespace and private-file review. Subsequent formatting-only Python changes preserve identical ASTs; the embedded historical Markdown template's intentional hard breaks are documented in `.gitattributes`.

Original source and documentation retain no general open-source license. Reviewed artwork is included for the owner's project publication on the basis recorded in [the provenance manifest](ASSET_PROVENANCE.json), without granting unrestricted downstream reuse. Third-party terms remain separate.

Excluded: `.git` metadata exports, `.venv`, personal saves/databases, credentials, raw generation/session directories, ignored `artifacts`, `build`, `dist`, wheels, backup archives, the duplicate legacy build spec and the root generated stress output. These exclusions do not delete local files.

This document records the original local review scope. The owner subsequently authorized its push and the integration of the final portfolio, including README polish commit `97b5165`, into the default `main` branch. Repository visibility is unchanged; no visibility change was included in that authorization.
