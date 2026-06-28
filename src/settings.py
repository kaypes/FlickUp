import json
from pathlib import Path

from gi.repository import GLib

_CONFIG_FILE = Path(GLib.get_user_config_dir()) / "flickup" / "settings.json"
_DEFAULTS: dict = {"last_format": ".mov", "send_to_drive": False}


def _load() -> dict:
    try:
        return {**_DEFAULTS, **json.loads(_CONFIG_FILE.read_text())}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def _save(data: dict) -> None:
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_last_format() -> str:
    return _load()["last_format"]


def save_last_format(fmt: str) -> None:
    data = _load()
    data["last_format"] = fmt
    _save(data)


def get_send_to_drive() -> bool:
    return bool(_load()["send_to_drive"])


def save_send_to_drive(value: bool) -> None:
    data = _load()
    data["send_to_drive"] = value
    _save(data)
