"""Isolated Contract automation test storage; previous test saves are not loaded."""
import os
from pathlib import Path

APP_SAVE_DIRECTORY_NAME = "Industriova"
PLAYTEST_SAVE_DIRECTORY_NAME = ("performance-test-20261025"
                                if os.environ.get("PRODUCTION_ZERO_PERFORMANCE_TEST") == "1"
                                else "contract-auto-test")


def default_save_directory() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    return (Path(root) if root else Path.home()) / APP_SAVE_DIRECTORY_NAME / "playtests" / PLAYTEST_SAVE_DIRECTORY_NAME / "saves"


def default_company_save_path() -> Path:
    return default_save_directory() / "company.sqlite"
