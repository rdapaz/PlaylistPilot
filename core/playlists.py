"""Turning tracks into playlist files and putting them where each player expects them."""
from __future__ import annotations

import ftplib
import io
import os
import re
from typing import Callable, Dict, Iterable, List, Optional

from .library import Track, ftp_connect
from .profiles import DeviceProfile

Progress = Callable[[str], None]


def _natkey(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def sort_tracks(tracks: Iterable[Track]) -> List[Track]:
    uniq = {t.key: t for t in tracks}
    return sorted(uniq.values(), key=lambda t: [_natkey(x) for x in (t.volume + "/" + t.rel).split("/")])


def entry_path(profile: DeviceProfile, t: Track) -> str:
    vol = next((v for v in profile.volumes if v.label == t.volume), None)
    path = (vol.prefix if vol else "") + t.rel
    if profile.separator == "\\":
        path = path.replace("/", "\\")
    return path


def render_m3u(profile: DeviceProfile, tracks: Iterable[Track], keep_order: bool = False) -> str:
    lines = ["#EXTM3U"]
    seq = list(tracks) if keep_order else sort_tracks(tracks)
    for t in seq:
        label = f"{t.artist} - {t.title}" if t.artist and t.artist.lower() != "various artists" else t.title
        lines.append(f"#EXTINF:-1,{label}")
        lines.append(entry_path(profile, t))
    return "\n".join(lines) + "\n"


def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "-", name).strip() or "playlist"


def write_local_copies(profile: DeviceProfile, playlists: Dict[str, str], local_root: str,
                       progress: Optional[Progress] = None) -> List[str]:
    folder = os.path.join(local_root, safe_name(profile.name))
    os.makedirs(folder, exist_ok=True)
    written = []
    for name, text in playlists.items():
        path = os.path.join(folder, safe_name(name) + profile.extension)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(path)
        if progress:
            progress(f"Saved {path}")
    return written


def deploy(profile: DeviceProfile, playlists: Dict[str, str], password: str = "",
           progress: Optional[Progress] = None) -> List[str]:
    """Write every playlist into each of the profile's deploy folders. Returns one line per file."""
    results: List[str] = []
    if profile.is_ftp:
        ftp = ftp_connect(profile, password, timeout=60)
        try:
            for folder in profile.deploy_dirs:
                for name, text in playlists.items():
                    data = text.encode("utf-8")
                    remote = f"{folder.rstrip('/')}/{safe_name(name)}{profile.extension}"
                    ftp.storbinary("STOR " + remote, io.BytesIO(data))
                    try:
                        ok = ftp.size(remote) == len(data)
                    except ftplib.error_perm:
                        ok = True
                    msg = f"{'OK' if ok else 'SIZE MISMATCH'}  {remote}"
                    results.append(msg)
                    if progress:
                        progress(msg)
        finally:
            try:
                ftp.quit()
            except Exception:
                pass
    else:
        for folder in profile.deploy_dirs:
            target = os.path.join(profile.usb_root, folder)
            os.makedirs(target, exist_ok=True)
            for name, text in playlists.items():
                path = os.path.join(target, safe_name(name) + profile.extension)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                msg = f"OK  {path}"
                results.append(msg)
                if progress:
                    progress(msg)
    return results
