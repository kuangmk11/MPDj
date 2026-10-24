"""One-time import of the old sidecar data. Read-only: nothing here writes to the library."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import lyrics, state
from .names import norm


def _read(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def import_lyrics(con: sqlite3.Connection, meta_dir: Path, log=print) -> int:
    """_lyrics/<artist>/<artist> - <title>.txt|.lrc. Names there are already lowercased/cleaned,
    and norm() of them matches norm() of the real tags closely enough."""
    root = meta_dir / "_lyrics"
    if not root.is_dir():
        log(f"  no {root}")
        return 0
    n = 0
    for f in sorted(root.rglob("*")):
        if f.suffix not in (".txt", ".lrc") or " - " not in f.stem:
            continue
        artist, title = f.stem.split(" - ", 1)
        if lyrics.get_cached(con, artist, title):
            continue
        text = _read(f).strip()
        if not text:
            continue
        if f.suffix == ".lrc":
            lyrics.save(con, artist, title, None, text, "legacy")
        else:
            lyrics.save(con, artist, title, text, None, "legacy")
        n += 1
    return n


def import_similar(con: sqlite3.Connection, meta_dir: Path, log=print) -> int:
    """__similar/<artist>.txt: one similar artist per line, best match first."""
    root = meta_dir / "__similar"
    if not root.is_dir():
        log(f"  no {root}")
        return 0
    n = 0
    for f in sorted(root.glob("*.txt")):
        artist = norm(f.stem)
        if con.execute("SELECT 1 FROM similar WHERE artist=? LIMIT 1", (artist,)).fetchone():
            continue  # already have fresher Last.fm data
        names = [l.strip() for l in _read(f).splitlines() if l.strip()]
        total = len(names) or 1
        con.executemany(
            "INSERT OR IGNORE INTO similar(artist,other,other_norm,match) VALUES(?,?,?,?)",
            [(artist, name, norm(name), round(1 - i / total, 3)) for i, name in enumerate(names)])
        n += 1
    return n


def import_blacklist(con: sqlite3.Connection, meta_dir: Path, log=print) -> int:
    f = meta_dir / "__suggestions" / "_blacklist.txt"
    if not f.exists():
        log(f"  no {f}")
        return 0
    names = [l.strip() for l in _read(f).splitlines() if l.strip()]
    con.executemany("INSERT OR IGNORE INTO suggest_ignore(norm,name) VALUES(?,?)",
                    [(norm(x), x) for x in names])
    return len(names)


def import_loved(con: sqlite3.Connection, music_dir: Path, playlist_dir: Path, log=print) -> int:
    """Files in loved-master.lin.m3u become 5 stars (unless already rated)."""
    n = 0
    for f in (playlist_dir / "linux/loved-master.lin.m3u",
              playlist_dir / "linux/mpdmela-lastfm-loved-tracks.m3u"):
        if not f.exists():
            log(f"  no {f}")
            continue
        for line in _read(f).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(str(music_dir)):
                line = line[len(str(music_dir)):].lstrip("/")
            if not con.execute("SELECT 1 FROM rating WHERE file=?", (line,)).fetchone():
                state.set_rating(con, line, 5)
                n += 1
    return n


def import_rating_tags(con: sqlite3.Connection, music_dir: Path, log=print) -> int:
    """ID3 TXXX:MYRATING frames written by the old mpd_*star.sh scripts. Slow on big libraries."""
    from mutagen.id3 import ID3, ID3NoHeaderError
    n = 0
    for f in music_dir.rglob("*.mp3"):
        try:
            frames = ID3(f).getall("TXXX:MYRATING")
        except (ID3NoHeaderError, OSError, Exception):
            continue
        if not frames:
            continue
        try:
            stars = int(str(frames[0].text[0]).strip())
        except (ValueError, IndexError):
            continue
        if 1 <= stars <= 5:
            rel = str(f.relative_to(music_dir))
            if not con.execute("SELECT 1 FROM rating WHERE file=?", (rel,)).fetchone():
                state.set_rating(con, rel, stars)
                n += 1
    return n
