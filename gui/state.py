"""Shared application state passed to every view."""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from core.genres import GenreMap
from core.library import Track
from core.profiles import DeviceProfile, load_profiles, save_profiles, find_profile
from core import settings


class AppState(QObject):
    device_changed = Signal()
    library_changed = Signal()
    genres_changed = Signal()
    logged = Signal(str)
    connection_changed = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.profiles: List[DeviceProfile] = load_profiles()
        self.profile: Optional[DeviceProfile] = None
        self.password: str = ""
        self.tracks: List[Track] = []
        self.genre_map = GenreMap()
        self.custom_playlists: Dict[str, List[Track]] = {}
        self.connected = False
        last = settings.last_device()
        self.select_device(find_profile(self.profiles, last) or self.profiles[0])

    # ---- devices
    def select_device(self, profile: DeviceProfile) -> None:
        if self.profile is profile:
            return
        self.profile = profile
        self.password = settings.remembered_password(profile.name)
        self.tracks = []
        self.custom_playlists = {}
        self.connected = False
        settings.set_last_device(profile.name)
        self.device_changed.emit()
        self.library_changed.emit()
        self.connection_changed.emit(False, "not connected")

    def save_profile(self, profile: DeviceProfile) -> None:
        names = [p.name for p in self.profiles]
        if profile.name in names:
            self.profiles[names.index(profile.name)] = profile
        else:
            self.profiles.append(profile)
        save_profiles([p for p in self.profiles])
        if self.profile and self.profile.name == profile.name:
            self.profile = profile
        self.device_changed.emit()

    def delete_profile(self, profile: DeviceProfile) -> None:
        self.profiles = [p for p in self.profiles if p.name != profile.name]
        save_profiles(self.profiles)
        self.profiles = load_profiles()      # a deleted built-in comes back in its default form
        if self.profile is None or self.profile.name == profile.name:
            self.profile = None
            self.select_device(self.profiles[0])
        else:
            self.device_changed.emit()

    # ---- library
    def set_tracks(self, tracks: List[Track]) -> None:
        self.tracks = tracks
        self.library_changed.emit()

    def set_connected(self, ok: bool, detail: str) -> None:
        self.connected = ok
        self.connection_changed.emit(ok, detail)

    def log(self, msg: str) -> None:
        self.logged.emit(msg)
