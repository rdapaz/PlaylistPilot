"""Soundiiz CSV in and out.

Soundiiz exports a playlist as CSV with the header
    Track name,Artist name,Album,Playlist name,Type,ISRC,Duration
and accepts the same shape back. Import rows carry no paths, so each row is fuzzy-matched against the
scanned device library on title + artist (+ album, duration when known)."""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Tuple

from .library import Track

SOUNDIIZ_HEADER = ["Track name", "Artist name", "Album", "Playlist name", "Type", "ISRC", "Duration"]

COLS = {
    "title": ["track name", "title", "track", "song", "name"],
    "artist": ["artist name", "artist", "artists", "artist(s)"],
    "album": ["album", "album name"],
    "playlist": ["playlist name", "playlist"],
    "isrc": ["isrc"],
    "dur": ["duration", "duration (ms)", "length"],
}


@dataclass
class CsvRow:
    title: str
    artist: str
    album: str = ""
    playlist: str = ""
    isrc: str = ""
    dur: int = 0
    n: Dict[str, str] = field(default_factory=dict)   # normalised forms, filled lazily


@dataclass
class Match:
    row: CsvRow
    track: Optional[Track]
    score: float
    manual: bool = False

    @property
    def ok(self) -> bool:
        return self.track is not None


# ----------------------------------------------------------------------------- normalisation (same idea as soundiiz2fb.py)
_PAREN = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")
_FEAT = re.compile(r"\b(feat|ft|featuring|with)\b.*$", re.I)
_NOISE = re.compile(r"\b(remaster(ed)?|\d{4} remaster|mono|stereo|single version|album version|radio edit|explicit|"
                    r"clean|deluxe|bonus track|live|edit|version|mix|original)\b", re.I)
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str, aggressive: bool = False) -> str:
    s = strip_accents(s or "").lower().replace("&", " and ")
    if aggressive:
        s = re.sub(r"\s[-–—]\s.*$", " ", s)
        s = _PAREN.sub(" ", s)
        s = _FEAT.sub(" ", s)
        s = _NOISE.sub(" ", s)
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


# ----------------------------------------------------------------------------- reading

def _pick_col(headers, wanted) -> Optional[str]:
    hl = [h.strip().lower() for h in headers]
    for w in wanted:
        if w in hl:
            return headers[hl.index(w)]
    for w in wanted:
        for i, h in enumerate(hl):
            if w in h:
                return headers[i]
    return None


def read_soundiiz_csv(path: str) -> List[CsvRow]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
        except csv.Error:
            dialect = csv.excel
        rd = csv.DictReader(fh, dialect=dialect)
        if not rd.fieldnames:
            raise ValueError("Empty CSV")
        cols = {k: _pick_col(rd.fieldnames, v) for k, v in COLS.items()}
        if not cols["title"] or not cols["artist"]:
            raise ValueError(f"Could not find title/artist columns in {rd.fieldnames}")
        rows: List[CsvRow] = []
        for r in rd:
            dur_s = (r.get(cols["dur"]) or "").strip() if cols["dur"] else ""
            try:
                dur = int(float(dur_s))
                dur = dur // 1000 if dur > 10000 else dur
            except ValueError:
                dur = 0
            title = (r.get(cols["title"]) or "").strip()
            artist = (r.get(cols["artist"]) or "").strip()
            if not title and not artist:
                continue
            rows.append(CsvRow(
                title=title, artist=artist,
                album=(r.get(cols["album"]) or "").strip() if cols["album"] else "",
                playlist=(r.get(cols["playlist"]) or "").strip() if cols["playlist"] else "",
                isrc=((r.get(cols["isrc"]) or "").strip().upper().replace("-", "")) if cols["isrc"] else "",
                dur=dur,
            ))
    return rows


# ----------------------------------------------------------------------------- matching

class LibraryIndex:
    """Pre-normalised view of the device library for fast repeated matching."""

    def __init__(self, tracks: Iterable[Track]):
        self.entries = []
        for t in tracks:
            self.entries.append({
                "t": t,
                "n_title": norm(t.title), "n_title_a": norm(t.title, True),
                "n_artist": norm(t.artist), "n_artist_a": norm(t.artist, True),
                "n_album": norm(t.album, True),
                "words": set(norm(t.title, True).split()) | set(norm(t.artist, True).split()),
            })

    def best(self, row: CsvRow) -> Tuple[Optional[Track], float]:
        if not row.n:
            row.n = {"t": norm(row.title), "ta": norm(row.title, True), "a": norm(row.artist),
                     "aa": norm(row.artist, True), "al": norm(row.album, True)}
        words = set(row.n["ta"].split()) | set(row.n["aa"].split())
        primary = row.n["aa"].split(" and ")[0].split(",")[0].strip()
        best, best_s = None, 0.0
        for e in self.entries:
            if words and not (words & e["words"]):
                continue
            t = max(sim(row.n["t"], e["n_title"]), sim(row.n["ta"], e["n_title_a"]))
            # medleys and combined titles ("Around The World , Harder Better Faster Stronger"): containment counts
            if t < 0.9 and len(row.n["ta"]) >= 8 and (f" {row.n['ta']} " in f" {e['n_title']} " or f" {e['n_title_a']} " in f" {row.n['ta']} "):
                t = max(t, 0.9)
            if t < 0.45:
                continue
            a = max(sim(row.n["a"], e["n_artist"]), sim(row.n["aa"], e["n_artist_a"]))
            if a < 0.8 and primary:
                a = max(a, sim(primary, e["n_artist_a"]) * 0.97)
            s = 0.6 * t + 0.4 * a
            if row.n["al"] and e["n_album"]:
                al_words = set(row.n["al"].split())
                contained = al_words and al_words <= set(e["n_album"].split())
                s += 0.05 * (1.0 if contained else sim(row.n["al"], e["n_album"]))
            if s > best_s:
                best, best_s = e["t"], s
        return best, best_s

    def search(self, text: str, limit: int = 60) -> List[Track]:
        q = norm(text)
        if not q:
            return []
        scored = []
        for e in self.entries:
            hay = f"{e['n_artist']} {e['n_title']} {e['n_album']}"
            if all(w in hay for w in q.split()):
                scored.append((0, e["t"]))
            else:
                s = sim(q, e["n_title"]) + 0.5 * sim(q, e["n_artist"])
                if s > 0.9:
                    scored.append((1 - s, e["t"]))
        scored.sort(key=lambda x: x[0])
        return [t for _, t in scored[:limit]]


def match_rows(rows: List[CsvRow], index: LibraryIndex, min_score: float = 0.80) -> List[Match]:
    out = []
    for row in rows:
        t, s = index.best(row)
        out.append(Match(row, t if s >= min_score else None, s))
    return out


# ----------------------------------------------------------------------------- writing

def write_soundiiz_csv(path: str, playlist_name: str, tracks: Iterable[Track]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(SOUNDIIZ_HEADER)
        for t in tracks:
            w.writerow([t.title, t.artist, t.album, playlist_name, "track", "", ""])
            n += 1
    return n


def rows_from_m3u(path: str) -> List[Tuple[str, str, str]]:
    """(title, artist, album) from an m3u/m3u8 written by PlaylistPilot or foobar2000: uses the EXTINF
    'Artist - Title' label and the parent folder as album."""
    out = []
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        label = ""
        for line in fh:
            line = line.rstrip("\r\n")
            if line.startswith("#EXTINF:"):
                label = line.split(",", 1)[1] if "," in line else ""
            elif line and not line.startswith("#"):
                parts = re.split(r"[\\/]", line)
                album = parts[-2] if len(parts) >= 2 else ""
                if " - " in label:
                    artist, title = label.split(" - ", 1)
                else:
                    artist, title = "", label or parts[-1].rsplit(".", 1)[0]
                out.append((title.strip(), artist.strip(), album))
                label = ""
    return out


def write_soundiiz_csv_rows(path: str, playlist_name: str, rows: Iterable[Tuple[str, str, str]]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(SOUNDIIZ_HEADER)
        for title, artist, album in rows:
            w.writerow([title, artist, album, playlist_name, "track", "", ""])
            n += 1
    return n
