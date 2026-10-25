from __future__ import annotations

import os
import sys

APP_NAME = "Industriova"
APP_VERSION = ("0.3.0.performance-test-20261025"
               if os.environ.get("PRODUCTION_ZERO_PERFORMANCE_TEST") == "1"
               else "0.3.0.contract-auto-test")


_development_default = "0" if getattr(sys, "frozen", False) else "1"
DEVELOPMENT_MODE = os.environ.get("PRODUCTION_ZERO_DEV_MODE", _development_default) not in {"0", "false", "False"}
CHARTS_ENABLED = os.environ.get("PRODUCTION_ZERO_CHARTS", "0") not in {"0", "false", "False"}
