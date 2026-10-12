"""App-wide settings kept in QSettings (the main window stores its geometry there too)."""
from __future__ import annotations

import os

from PySide6.QtCore import QSettings

ORG, APP = "ricdeez", "PlaylistPilot"
_NAS = r"X:\music\playlists"
DEFAULT_PLAYLIST_ROOT = _NAS if os.path.isdir(_NAS) else os.path.join(os.path.expanduser("~"), "Music", "playlists")
DEFAULT_MODEL = "claude-opus-5-5"
MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]


def qs() -> QSettings:
    return QSettings(ORG, APP)


def playlist_root() -> str:
    return str(qs().value("playlist_root", DEFAULT_PLAYLIST_ROOT))


def set_playlist_root(path: str) -> None:
    qs().setValue("playlist_root", path)


def api_key() -> str:
    return str(qs().value("anthropic_api_key", "")) or os.environ.get("ANTHROPIC_API_KEY", "")


def set_api_key(key: str) -> None:
    qs().setValue("anthropic_api_key", key)


def model() -> str:
    return str(qs().value("claude_model", DEFAULT_MODEL))


def set_model(m: str) -> None:
    qs().setValue("claude_model", m)


def remembered_password(profile_name: str) -> str:
    return str(qs().value(f"pw/{profile_name}", ""))


def remember_password(profile_name: str, pw: str) -> None:
    if pw:
        qs().setValue(f"pw/{profile_name}", pw)
    else:
        qs().remove(f"pw/{profile_name}")


def last_device() -> str:
    return str(qs().value("last_device", ""))


def set_last_device(name: str) -> None:
    qs().setValue("last_device", name)
