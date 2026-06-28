import json
from pathlib import Path

from gi.repository import GLib

_CONFIG_FILE = Path(GLib.get_user_config_dir()) / "flickup" / "settings.json"
_DEFAULTS: dict = {"last_format": ".mov"}


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
