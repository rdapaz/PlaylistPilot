"""Device profiles: how to reach a player, how its library is laid out, and how it wants playlists written.

Profiles come from three layers, later ones winning by name:
  1. devices.example.json  - shipped with the app, placeholder addresses
  2. devices.json          - your real players, next to main.py, git-ignored
  3. ~/.playlistpilot/devices.json - whatever you add or edit inside the app
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

APP_DIR = os.path.join(os.path.expanduser("~"), ".playlistpilot")
PROFILES_FILE = os.path.join(APP_DIR, "devices.json")
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICES_FILE = os.path.join(PROJECT_DIR, "devices.json")
EXAMPLE_FILE = os.path.join(PROJECT_DIR, "devices.example.json")


@dataclass
class Volume:
    """One storage area the player exposes.

    label  - the folder name as the FTP server lists it (or the sub-folder under the USB root).
    prefix - what to put in front of the relative path in a playlist entry. Empty means
             "write the path relative to the playlist's own folder".
    """
    label: str
    prefix: str = ""


@dataclass
class DeviceProfile:
    name: str
    kind: str = "ftp"                      # "ftp" | "usb"
    host: str = ""
    port: int = 2100
    user: str = ""
    usb_root: str = ""                     # e.g. "D:\\"
    volumes: List[Volume] = field(default_factory=list)
    deploy_dirs: List[str] = field(default_factory=list)   # FTP dirs or USB sub-folders to drop playlists into
    separator: str = "/"                   # "/" or "\\"
    extension: str = ".m3u8"
    decode_percent: bool = False           # iPhone: FTP lists %xx, playlists need the real characters
    skip_dirs: List[str] = field(default_factory=lambda: [".thumbnails", "Skins", "Android", "System Volume Information"])
    guidance: str = ""
    builtin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "DeviceProfile":
        d = {k: v for k, v in d.items() if k in DeviceProfile.__dataclass_fields__}
        d["volumes"] = [Volume(**v) for v in d.get("volumes", [])]
        return DeviceProfile(**d)

    @property
    def is_ftp(self) -> bool:
        return self.kind == "ftp"


FTP_GUIDE = (
    "1. On the player open foobar2000 mobile, go to Tools > FTP Server and turn it on.\n"
    "2. Note the address and port it shows. Keep the screen awake: the server stops when the screen locks.\n"
    "3. Enter the address, port and login below, then press Test connection.\n"
    "4. Press Scan library. The whole tree is listed over FTP, which takes a few minutes for 10,000 files.\n"
    "5. Build or compose playlists, then Deploy. Files are uploaded to every deploy folder and verified by size."
)

USB_GUIDE = (
    "1. Connect the player with its USB cable and, if asked, choose file transfer / mass storage.\n"
    "2. Wait for the card to appear as a drive letter in Explorer and enter it below (for example D:\\).\n"
    "3. Press Test connection to confirm the music folder is visible, then Scan library.\n"
    "4. Build or compose playlists, then Deploy. Files are written into the playlist folder on the card.\n"
    "5. Safely eject the drive. On a Shanling: My Music > Playlists > three dots > Import Playlist."
)
GUIDES = {"ftp": FTP_GUIDE, "usb": USB_GUIDE}


def _read_profile_file(path: str, builtin: bool) -> List[DeviceProfile]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for d in data if isinstance(data, list) else []:
        try:
            d = dict(d)
            d.setdefault("guidance", "") or d.__setitem__("guidance", GUIDES.get(d.get("kind", "ftp"), FTP_GUIDE))
            d["builtin"] = builtin
            out.append(DeviceProfile.from_dict(d))
        except (TypeError, ValueError):
            continue
    return out


def builtin_profiles() -> List[DeviceProfile]:
    """devices.json if you have one, otherwise the shipped example."""
    source = DEVICES_FILE if os.path.exists(DEVICES_FILE) else EXAMPLE_FILE
    profiles = _read_profile_file(source, builtin=True)
    if not profiles:
        profiles = [DeviceProfile(name="My player", kind="ftp", port=2100, guidance=FTP_GUIDE, builtin=True,
                                  volumes=[Volume("foobar2000 Music Folder", "")], deploy_dirs=["/foobar2000 Music Folder"])]
    return profiles


def profiles_source() -> str:
    return DEVICES_FILE if os.path.exists(DEVICES_FILE) else EXAMPLE_FILE


def load_profiles() -> List[DeviceProfile]:
    """Built-ins first, then anything the user saved in the app (saved copies of a built-in override it)."""
    profiles = {p.name: p for p in builtin_profiles()}
    for p in _read_profile_file(PROFILES_FILE, builtin=False):
        p.builtin = p.name in profiles and profiles[p.name].builtin
        profiles[p.name] = p
    return list(profiles.values())


def save_profiles(profiles: List[DeviceProfile]) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump([p.to_dict() for p in profiles], f, indent=2, ensure_ascii=False)


def find_profile(profiles: List[DeviceProfile], name: str) -> Optional[DeviceProfile]:
    return next((p for p in profiles if p.name == name), None)
