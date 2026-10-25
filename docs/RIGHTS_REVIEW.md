# Rights and dependency review

Review date: 25 October 2026. Status: **owner-confirmed asset origin; no general open-source license; publication approval pending**.

## Source and documentation decision

The owner instructed that original source and documentation remain without a general open-source license. The earlier MIT proposal is not adopted. [RIGHTS.md](../RIGHTS.md) records this decision without relabeling third-party material or claiming that all AI output necessarily attracts copyright. No general license grant has been added. GitHub's platform permissions for a future public repository remain applicable; see [GitHub's explanation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

Dependencies retain their own licenses. The project rights notice does not replace Qt obligations or restrict permissions granted by dependency licenses. A future packaged executable needs its own distribution review.

## Assets and screenshots

[ASSET_INVENTORY.csv](ASSET_INVENTORY.csv) lists every application asset and portfolio screenshot with size, SHA-256 and publication status. [ASSET_PROVENANCE.json](ASSET_PROVENANCE.json) binds the exact files to the owner's declaration of 25 October 2026: all artwork was generated with GPT without external templates. This is an explicit creator declaration, not an independently retrieved generation receipt for every image.

| Group | Technical evidence | Publication basis |
| --- | --- | --- |
| Resource artwork and atlas | Four integration manifests cover 353 resources; the atlas records source hashes | Owner declaration covers generated originals and their derived masks, scaling and atlas |
| Machine artwork | Machine/energy QA reports and byte-identical primary-card reports | Same declaration; no external templates according to the owner |
| Freight artwork | Four current PNG hashes match their raster integration reports | Same declaration; historical references were supplied generated images, without an asserted external source |
| Research icon | Original-source hash, mask audit and current derived file | Same declaration; mask processing is not a separate image generator |
| Portfolio screenshots | Synthetic current application renders with capture manifest | Derived from the same reviewed artwork; no personal save data |

No external font files are included in the candidate. Capture tools load installed Windows fonts without copying their files into the repository. Their names and rendered appearance are not evidence that font binaries may be redistributed.

OpenAI's [Europe Terms of Use](https://openai.com/policies/eu-terms-of-use/) assign OpenAI's rights, if any, in output to the user to the extent permitted by law, while making the user responsible for inputs and respecting third-party rights. Output need not be unique. These terms and the owner's no-template declaration support the owner's project publication; they do not establish exclusivity or grant a license to repository visitors.

The checked files are classified separately from unreviewed material. A file is eligible only while its exact SHA-256 matches the owner-confirmed provenance record; missing or changed records are marked pending and must not be staged for release. No new general permission is needed merely because an asset was AI-generated. Individual historical prompts or generation receipts were not available for every asset; that evidentiary limit remains explicit. No foreign-template exception or unresolved third-party source was identified in the supplied record after the owner's clarification.

## Dependencies inspected

The local environment contains the following verified package metadata. [DEPENDENCY_INVENTORY.csv](DEPENDENCY_INVENTORY.csv) additionally records the complete 16-package installed dependency closure of PySide6, pytest, PyInstaller and the setuptools build backend for this Windows/Python environment, including transitive tooling dependencies. Installation artifacts are excluded; the source checkout depends on packages rather than vendoring their binaries. Development requirements have lower bounds rather than a lockfile, so this inventory records the inspected environment and does not promise identical future resolutions.

| Component | Inspected version | Terms/evidence and next action |
| --- | --- | --- |
| Python | 3.12.14 | PSF and incorporated component terms; retain applicable notices if distributing a runtime. [Python license](https://docs.python.org/3/license.html) |
| PySide6, Essentials, Addons, shiboken6 | 6.11.1 each | Installed metadata: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only. Qt module and bundled third-party terms still require review for binary distribution. [Qt for Python](https://doc.qt.io/qtforpython-6/), [Qt licensing](https://doc.qt.io/qt-6/licensing.html) |
| pytest | 9.1.1 | Installed metadata identifies MIT; development only |
| PyInstaller | 6.22.2 | Installed metadata identifies GPL with bundling exception; some upstream files have Apache terms. The exception does not override dependency terms. [Upstream licensing](https://pyinstaller.org/en/stable/license.html) |
| setuptools | 84.0.0 | Installed metadata identifies MIT; build tooling |

Static Python imports in the application source use QtCore, QtGui, QtWidgets, QtSvg and QtTest. This is an import inventory, not certification of every Qt library or plugin a PyInstaller bundle may collect. The dependency on PySide6 also installs Addons; a future binary release needs an actual bundled-module and notice inventory. [Qt's obligations guidance](https://www.qt.io/development/open-source-lgpl-obligations) distinguishes module licenses and LGPL requirements.

Historical, optional image-processing tools import Pillow, NumPy and OpenCV. These packages were not installed in the reviewed game environment, are not vendored, and those workflows were not executed. Verify the chosen versions and notices if reviving or distributing that tool environment. Source code uses Python's SQLite module; any future bundled interpreter also needs its incorporated-component notices reviewed.

This review separates owner testimony, technical file provenance and provider terms. It does not claim independent generation receipts for every image, exclusive copyright in AI output or a dependency vulnerability audit. The source rights decision is settled for this preparation. Any future new asset, binary bundle or third-party exception requires its own review before publication.
