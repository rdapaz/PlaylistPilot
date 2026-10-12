"""Scanning a player's library (over FTP or from a mounted drive) into a flat list of tracks."""
from __future__ import annotations

import ftplib
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional
from urllib.parse import unquote

from .profiles import DeviceProfile

AUDIO_EXT = (".flac", ".mp3", ".m4a", ".ogg", ".opus", ".wav", ".aiff", ".ape", ".wv", ".dsf", ".dff", ".alac")
Progress = Callable[[str], None]


@dataclass
class Track:
    volume: str          # volume label (as the profile names it)
    rel: str             # path below the volume root, forward slashes, decoded (real characters)
    artist: str = ""
    album: str = ""
    title: str = ""
    genre_tag: str = ""  # from file tags when available (USB scans only)

    @property
    def filename(self) -> str:
        return self.rel.rsplit("/", 1)[-1]

    @property
    def key(self) -> str:
        return f"{self.volume}/{self.rel}"


_HEAD_SPLIT = re.compile(r"\s+[-–]\s+|-Ao vivo|\s+DISCOGRAPHY\b|\s+Discography\b", re.I)
_YEAR = re.compile(r"^[\(\[]\d{4}[\)\]]\s*")
_NUM = re.compile(r"^(?:[A-D]\d{1,2}\.?\s+)|^(?:\d{1,2}[\s._-]+)?(?:\d{1,3}[\s._-]+)")
_DISC = re.compile(r"^(cd|disc|disk|side)\s*\d+|^(flac|mp3|wav|original|covers?|scans?|artwork)$", re.I)


def _head(name: str) -> str:
    return _HEAD_SPLIT.split(_YEAR.sub("", name), maxsplit=1)[0].strip()


def infer_artist_album(rel: str) -> tuple:
    """Best effort from the folder structure. Handles <Letter>/<Artist>/<Album>/, Misc/<Artist - Album>/,
    flat <Artist - Album>/ dumps and loose files."""
    parts = rel.split("/")
    if len(parts) == 1:
        return _head(parts[0].rsplit(".", 1)[0]), ""
    p0 = parts[0]
    letterish = len(p0) == 1 or p0.lower() in ("misc", "various", "yt", "0-9", "#")
    if letterish and len(parts) >= 3:
        if p0.lower() == "misc":
            artist = _head(parts[1])
            album = parts[2] if len(parts) >= 4 else parts[1].split(" - ", 1)[-1]
        else:
            artist, album = parts[1], (parts[2] if len(parts) >= 4 else "")
        return artist, album
    if letterish and len(parts) == 2:
        return _head(parts[1].rsplit(".", 1)[0]), ""
    artist = _head(p0)
    own_album = p0.split(" - ", 1)[1] if " - " in p0 else p0
    if len(parts) >= 3 and not _DISC.match(parts[1]):
        album = parts[1]
    else:                               # "Artist - Album/CD1/track" or ".../FLAC/track": the album is the parent
        album = own_album
    return artist, _YEAR.sub("", album)


def infer_title(rel: str, artist: str) -> str:
    stem = rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if " - " in stem and re.search(r" - \d{1,2}-\d{2,3} ", stem):
        stem = re.split(r" - \d{1,2}-\d{2,3} ", stem, maxsplit=1)[1]
    stem = _NUM.sub("", stem).strip(" -._")
    if artist and stem.lower().startswith(artist.lower() + " - "):
        stem = stem[len(artist) + 3:]
    return stem or rel.rsplit("/", 1)[-1]


def make_track(volume: str, rel: str) -> Track:
    artist, album = infer_artist_album(rel)
    return Track(volume=volume, rel=rel, artist=artist, album=album, title=infer_title(rel, artist))


def _is_audio(name: str) -> bool:
    return name.lower().endswith(AUDIO_EXT) and not name.startswith("._")


# ----------------------------------------------------------------------------- FTP

def ftp_connect(profile: DeviceProfile, password: str, timeout: int = 30) -> ftplib.FTP:
    ftp = ftplib.FTP()
    ftp.encoding = "utf-8"
    ftp.connect(profile.host, profile.port, timeout=timeout)
    ftp.login(profile.user, password)
    return ftp


def ftp_list_root(profile: DeviceProfile, password: str) -> List[str]:
    ftp = ftp_connect(profile, password, timeout=15)
    try:
        return [n for n, f in ftp.mlsd("/") if f.get("type") == "dir"]
    finally:
        ftp.quit()


def scan_ftp(profile: DeviceProfile, password: str, progress: Optional[Progress] = None) -> List[Track]:
    ftp = ftp_connect(profile, password)
    tracks: List[Track] = []
    count = {"dirs": 0}

    def walk(path: str, volume: str, base: str):
        count["dirs"] += 1
        for name, facts in list(ftp.mlsd(path)):
            if name in (".", "..") or name in profile.skip_dirs:
                continue
            full = path.rstrip("/") + "/" + name
            if facts.get("type") == "dir":
                walk(full, volume, base)
            elif _is_audio(name):
                rel = full[len(base):].lstrip("/")
                if profile.decode_percent:
                    rel = unquote(rel)
                tracks.append(make_track(volume, rel))
        if progress and count["dirs"] % 25 == 0:
            progress(f"{count['dirs']} folders, {len(tracks)} tracks so far")

    try:
        for vol in profile.volumes:
            base = "/" + vol.label
            if progress:
                progress(f"Scanning {vol.label} ...")
            try:
                walk(base, vol.label, base)
            except ftplib.error_perm as e:
                if progress:
                    progress(f"Skipped {vol.label}: {e}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
    return tracks


# ----------------------------------------------------------------------------- USB / local

def scan_local(profile: DeviceProfile, progress: Optional[Progress] = None, read_tags: bool = False) -> List[Track]:
    tracks: List[Track] = []
    root = profile.usb_root
    for vol in profile.volumes:
        base = os.path.join(root, vol.label)
        if not os.path.isdir(base):
            if progress:
                progress(f"Missing folder: {base}")
            continue
        if progress:
            progress(f"Scanning {base} ...")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in profile.skip_dirs]
            for fn in filenames:
                if not _is_audio(fn):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), base).replace(os.sep, "/")
                t = make_track(vol.label, rel)
                if read_tags:
                    _apply_tags(os.path.join(dirpath, fn), t)
                tracks.append(t)
            if progress and tracks and len(tracks) % 500 == 0:
                progress(f"{len(tracks)} tracks so far")
    return tracks


def _apply_tags(path: str, t: Track) -> None:
    try:
        import mutagen  # optional dependency
        audio = mutagen.File(path, easy=True)
        if not audio:
            return

        def first(k):
            v = audio.get(k)
            return str(v[0]).strip() if v else ""

        t.artist = first("albumartist") or first("artist") or t.artist
        t.album = first("album") or t.album
        t.title = first("title") or t.title
        t.genre_tag = first("genre")
    except Exception:
        pass


# ----------------------------------------------------------------------------- listing files

def save_listing(tracks: Iterable[Track], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in tracks:
            f.write(f"{t.volume}/{t.rel}\n")


def load_listing(path: str, profile: DeviceProfile) -> List[Track]:
    labels = sorted((v.label for v in profile.volumes), key=len, reverse=True)
    out: List[Track] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").lstrip("/")
            if not line or not _is_audio(line.rsplit("/", 1)[-1]):
                continue
            for lab in labels:
                if line.startswith(lab + "/"):
                    rel = line[len(lab) + 1:]
                    out.append(make_track(lab, unquote(rel) if profile.decode_percent else rel))
                    break
    return out
