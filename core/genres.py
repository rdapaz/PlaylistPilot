"""Genre rules: a hand-built artist map (everything learnt from the four players), keyword rules for
loose mixes, optional Claude classification for whatever is left, and per-artist overrides."""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from .library import Track
from .profiles import APP_DIR

GENRES = ["Heavy Metal", "Trip Hop", "R&B", "Study", "Coding", "Brazilian", "Classical", "Vangelis", "Jazz"]
GENRE_HINTS = {
    "Heavy Metal": "metal in the broad sense: thrash, nu-metal, metalcore, industrial metal, prog metal, stoner metal, proto-metal hard rock like Deep Purple or Black Sabbath",
    "Trip Hop": "Bristol-style trip hop and close relatives (Massive Attack, Portishead, Gorillaz)",
    "R&B": "R&B, soul, Motown, neo-soul and contemporary R&B/pop-soul (Adele, Amy Winehouse, The Weeknd)",
    "Study": "calm music to study to: ambient, classical, new age, chant, soft instrumental, Vangelis, Enigma",
    "Coding": "driving electronic music to code to: big beat, techno, house, synth, dubstep, Jarre, Chemical Brothers",
    "Brazilian": "Brazilian artists: samba, MPB, bossa nova, Brazilian rock or pop",
    "Classical": "classical, opera and orchestral recordings",
    "Vangelis": "Vangelis only",
    "Jazz": "jazz, vocal jazz standards, bossa-jazz",
}

# artist (lower-case) -> list of genres
ARTIST_GENRES: Dict[str, List[str]] = {}


def _add(genre: str, *artists: str) -> None:
    for a in artists:
        ARTIST_GENRES.setdefault(a.lower(), []).append(genre)


_add("Heavy Metal", "Animals as Leaders", "Bad Omens", "Bad Omens (feat. Kayzo)", "Bring Me The Horizon", "Deftones",
     "Disturbed", "ERRA", "Evanescence", "Evansescence", "Gojira", "Invent Animate", "Lindemann", "Till Lindemann",
     "Linkin Park", "Jay-Z / Linkin Park", "Jay-Z ／ Linkin Park", "Limp Bizkit", "Meshuggah", "Ocean Grove",
     "Rammstein", "Rage Against The Machine", "Sepultura", "Slayer", "Slipknot", "System Of A Down", "TOOL", "Tesseract",
     "Thornhill", "Black Sabbath", "Marilyn Manson", "1000mods", "Deep Purple", "KoЯn", "Korn", "Isis")
_add("Trip Hop", "Massive Attack", "Portishead", "Gorillaz")
_add("R&B", "The Weeknd", "Bruno Mars", "Sade", "Amy Winehouse", "Adele", "Michael Jackson", "Donny Hathaway", "Drake")
_add("Study", "Vangelis", "Enigma", "Harold Budd", "Steve Roach", "Steve Roach & Soriah", "Robert Rich",
     "Robert Rich & Markus Reuter", "Brian Eno & Beatie Wolfe", "Brian Eno, Daniel Lanois, Roger Eno", "Roger Eno",
     "Brian Eno", "Bass Communion", "Tangerine Dream", "Johann Johannsson", "Jóhann Jóhannsson")
_add("Coding", "Daft Punk", "Alive 2007", "Deadmau5", "The Chemical Brothers", "Jean Michel Jarre", "Jean-Michel Jarre",
     "HACK THE PLANET", "Xenia Dia", "Xenia Diamond", "Melodic Techno", "Underworld")
_add("Brazilian", "Martinho Da Vila", "Seu Jorge", "Rita Lee", "Ana Carolina e Seu Jorge", "Ana Carolina")
_CLASSICAL = ["Antonio Vivaldi", "Beethoven", "Philharmonia Orchestra, Riccardo Muti",
              "Philharmonia Orchestra, Riccardo Muti (5-8)", "The Philadelphia Orchestra, Riccardo Muti", "Villa-Lobos",
              "Pastoral Symphony", "Academy of St. Martin in the Fields", "Karl Böhm, Wiener Philharmoniker",
              "Haydn", "Schubert", "Wolfgang Amadeus Mozart", "Yuja Wang"]
_add("Classical", *_CLASSICAL, "Luciano Pavarotti")
_add("Study", *_CLASSICAL)          # instrumental classical doubles as study music
_add("Vangelis", "Vangelis")
_add("Jazz", "Art Pepper", "Bill Evans Trio", "Frank Sinatra", "Miles Davis", "Miles Davis Quintet", "Stan Getz",
     "Stan Getz Quartet", "Stan Getz & Joao Gilberto")

# Album / folder name rules (regex on album + path), used for compilations and loose mixes
ALBUM_RULES = [
    ("R&B", re.compile(r"motown|r&b music for headphones", re.I)),
    ("Classical", re.compile(r"classical music for headphones", re.I)),
    ("Study", re.compile(r"classical music for headphones|gregorian|zen |meditation|focus temple|chillout|relaxation", re.I)),
    ("Coding", re.compile(r"coding music|hacker|future garage|techno|def con|dubstep|afro house|progressive house", re.I)),
    ("Heavy Metal", re.compile(r"paris live", re.I)),
]
EXCLUDE_ALBUM = re.compile(r"tribute|bootleg", re.I)

OVERRIDES_FILE = os.path.join(APP_DIR, "artist_overrides.json")
CLAUDE_CACHE_FILE = os.path.join(APP_DIR, "claude_genres.json")


def _load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_json(path: str, data: dict) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def norm_artist(a: str) -> str:
    a = a.lower().strip()
    return re.split(r"\s*;\s*|\s*\(\s*feat", a)[0].strip()


class GenreMap:
    """Resolves an artist to genres: manual overrides > built-in rules > Claude cache, plus album rules."""

    def __init__(self):
        self.overrides: Dict[str, List[str]] = _load_json(OVERRIDES_FILE)
        self.claude: Dict[str, List[str]] = _load_json(CLAUDE_CACHE_FILE)

    def artist_genres(self, artist: str) -> List[str]:
        a = norm_artist(artist)
        if a in self.overrides:
            return [g for g in self.overrides[a] if g in GENRES]
        found = list(ARTIST_GENRES.get(a, []))
        if not found:
            for key, gs in ARTIST_GENRES.items():
                if len(key) > 3 and a.startswith(key) and not a[len(key):len(key) + 1].isalnum():
                    found = list(gs)
                    break
        if not found and a in self.claude:
            found = [g for g in self.claude[a] if g in GENRES]
        return found

    def genres_for(self, t: Track) -> List[str]:
        folder = t.rel.rsplit("/", 1)[0] if "/" in t.rel else ""
        hay = f"{t.album} / {folder} / {t.rel if not folder else ''}"   # loose files: match on the file name too
        if EXCLUDE_ALBUM.search(hay):
            return []
        found = self.artist_genres(t.artist)
        for g, rx in ALBUM_RULES:
            if rx.search(hay) and g not in found:
                found.append(g)
        return found

    def source(self, artist: str) -> str:
        a = norm_artist(artist)
        if a in self.overrides:
            return "manual"
        if a in ARTIST_GENRES:
            return "rule"
        if a in self.claude:
            return "claude"
        return ""

    def set_override(self, artist: str, genres: List[str]) -> None:
        self.overrides[norm_artist(artist)] = [g for g in genres if g in GENRES]
        _save_json(OVERRIDES_FILE, self.overrides)

    def clear_override(self, artist: str) -> None:
        self.overrides.pop(norm_artist(artist), None)
        _save_json(OVERRIDES_FILE, self.overrides)

    def unknown_artists(self, tracks: Iterable[Track]) -> Dict[str, List[str]]:
        """artist -> sample albums, for artists that no override, rule or cached Claude answer places."""
        out: Dict[str, set] = defaultdict(set)
        for t in tracks:
            if not t.artist or self.source(t.artist):
                continue
            if self.genres_for(t):
                continue
            out[t.artist].add(t.album)
        return {k: sorted(x for x in v if x)[:4] for k, v in out.items()}

    def remember_claude(self, mapping: Dict[str, List[str]]) -> None:
        for artist, gs in mapping.items():
            self.claude[norm_artist(artist)] = [g for g in gs if g in GENRES]
        _save_json(CLAUDE_CACHE_FILE, self.claude)


def group_by_genre(tracks: Iterable[Track], gm: GenreMap) -> Dict[str, List[Track]]:
    out: Dict[str, List[Track]] = {g: [] for g in GENRES}
    for t in tracks:
        for g in gm.genres_for(t):
            out[g].append(t)
    return out


# ----------------------------------------------------------------------------- Claude

CLAUDE_SYSTEM = (
    "You classify music artists into playlist genres for a personal music library. "
    "You are given artist names with a few of their album titles. For each artist choose zero or more genres "
    "from the allowed list, using the genre descriptions. Prefer an empty list over a doubtful match. "
    "Respond with JSON only: an object mapping each artist name exactly as given to a list of genre names."
)


def classify_with_claude(unknown: Dict[str, List[str]], api_key: Optional[str], model: str,
                         progress=None) -> Dict[str, List[str]]:
    """Ask Claude to place unknown artists. Returns {artist: [genres]}. Raises on API failure."""
    import anthropic

    if not unknown:
        return {}
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    hints = "\n".join(f"- {g}: {d}" for g, d in GENRE_HINTS.items())
    result: Dict[str, List[str]] = {}
    items = list(unknown.items())
    batch = 60
    for i in range(0, len(items), batch):
        chunk = dict(items[i:i + batch])
        if progress:
            progress(f"Asking Claude about artists {i + 1}-{min(i + batch, len(items))} of {len(items)} ...")
        listing = "\n".join(f"{a}: {'; '.join(al) if al else '(no album info)'}" for a, al in chunk.items())
        prompt = (
            f"Allowed genres and what they mean:\n{hints}\n\n"
            f"Artists (name: sample albums):\n{listing}\n\n"
            'Return JSON: {"Artist Name": ["Genre", ...], ...} with every artist present.'
        )
        response = client.messages.create(
            model=model, max_tokens=8000, system=CLAUDE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude declined the classification request.")
        text = "".join(b.text for b in response.content if b.type == "text")
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        for a in chunk:
            gs = data.get(a, [])
            result[a] = [g for g in gs if g in GENRES] if isinstance(gs, list) else []
    return result
