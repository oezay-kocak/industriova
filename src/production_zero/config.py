from __future__ import annotations

import os


DEVELOPMENT_MODE = os.environ.get("PRODUCTION_ZERO_DEV_MODE", "1") not in {"0", "false", "False"}
FACTORY_VIEW_V2_ENABLED = os.environ.get("PRODUCTION_ZERO_FACTORY_VIEW_V2", "0") in {"1", "true", "True"}
