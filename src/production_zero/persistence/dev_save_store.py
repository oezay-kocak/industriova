from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


SAVE_VERSION = 1
DEV_SAVE_DIRECTORY = Path("saves") / "dev"
DEV_SAVE_FILENAME = "dev_save.json"


class DevSaveError(Exception):
    """Base class for developer save failures."""


class SaveNotFoundError(DevSaveError):
    pass


class InvalidSaveError(DevSaveError):
    pass


class IncompatibleSaveVersionError(DevSaveError):
    pass


class DevJsonSaveStore:
    def __init__(self, save_directory: Path = DEV_SAVE_DIRECTORY, filename: str = DEV_SAVE_FILENAME) -> None:
        self._save_directory = save_directory
        self._filename = filename

    @property
    def path(self) -> Path:
        return self._save_directory / self._filename

    def save(self, state: GameState) -> Path:
        self._save_directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "save_version": SAVE_VERSION,
            "state": serialize_game_state(state),
        }
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self._save_directory,
            prefix=f".{self._filename}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temp_path.replace(self.path)
        return self.path

    def load(self) -> GameState:
        if not self.path.exists():
            raise SaveNotFoundError(f"Save file does not exist: {self.path}")
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise InvalidSaveError("Save file is not valid JSON.") from exc
        except OSError as exc:
            raise InvalidSaveError("Save file could not be read.") from exc

        if not isinstance(payload, dict):
            raise InvalidSaveError("Save payload must be a JSON object.")
        save_version = payload.get("save_version")
        if save_version != SAVE_VERSION:
            raise IncompatibleSaveVersionError(f"Unsupported save_version: {save_version!r}")
        state_payload = payload.get("state")
        if not isinstance(state_payload, dict):
            raise InvalidSaveError("Save payload is missing state data.")
        try:
            return deserialize_game_state(state_payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidSaveError("Save state data is incomplete or invalid.") from exc
