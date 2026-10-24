"""Lyrics from LRCLIB (free, no key, often time-synced), cached in the DB."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import requests

from . import db
from .names import first, norm, norm_title

LRCLIB = "https://lrclib.net/api"
_TS = re.compile(r"^\s*\[\d+:\d+(?:[.:]\d+)?\]\s?", re.M)


def strip_timestamps(lrc: str) -> str:
    return _TS.sub("", lrc).strip()


def get_cached(con: sqlite3.Connection, artist: str, title: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM lyrics WHERE artist=? AND title=?",
                       (norm(artist), norm_title(title))).fetchone()


def save(con: sqlite3.Connection, artist: str, title: str, plain: str | None,
         synced: str | None, source: str) -> None:
    con.execute(
        "INSERT INTO lyrics(artist,title,plain,synced,source,fetched_at) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(artist,title) DO UPDATE SET plain=excluded.plain, synced=excluded.synced, "
        "source=excluded.source, fetched_at=excluded.fetched_at",
        (norm(artist), norm_title(title), plain, synced, source, db.now()),
    )


def delete(con: sqlite3.Connection, artist: str, title: str) -> int:
    return con.execute("DELETE FROM lyrics WHERE artist=? AND title=?",
                       (norm(artist), norm_title(title))).rowcount


def fetch_lrclib(artist: str, title: str, album: str = "", duration: float | None = None,
                 http: requests.Session | None = None) -> dict | None:
    http = http or requests.Session()
    headers = {"User-Agent": "mpdj/0.1 (personal MPD helper)"}
    params = {"artist_name": artist, "track_name": title}
    if album:
        params["album_name"] = album
    if duration:
        params["duration"] = int(round(duration))
    r = http.get(f"{LRCLIB}/get", params=params, headers=headers, timeout=15)
    if r.status_code == 200:
        return r.json()
    # Album/duration often differ from LRCLIB's copy; fall back to a search.
    r = http.get(f"{LRCLIB}/search", params={"artist_name": artist, "track_name": title},
                 headers=headers, timeout=15)
    if r.status_code != 200:
        return None
    want_a, want_t = norm(artist), norm_title(title)
    for hit in r.json():
        if norm(hit.get("artistName")) == want_a and norm_title(hit.get("trackName")) == want_t:
            if hit.get("plainLyrics") or hit.get("syncedLyrics") or hit.get("instrumental"):
                return hit
    return None


def lookup(con: sqlite3.Connection, song: dict, refresh: bool = False) -> sqlite3.Row | None:
    """Lyrics for an MPD song dict: DB first, then LRCLIB. Misses are remembered for a week."""
    artist, title = first(song.get("artist")), first(song.get("title"))
    if not artist or not title:
        return None
    row = get_cached(con, artist, title)
    if row and not refresh:
        return row
    key = f"{norm(artist)}|{norm_title(title)}"
    if not refresh and db.is_fresh(con, "lyrics", key, 7 * 86400):
        return row
    try:
        dur = song.get("duration") or song.get("time")
        hit = fetch_lrclib(artist, title, first(song.get("album")), float(dur) if dur else None)
    except (requests.RequestException, ValueError):
        db.mark_fetched(con, "lyrics", key, False)
        return row
    if hit:
        plain = "[instrumental]" if hit.get("instrumental") else hit.get("plainLyrics")
        save(con, artist, title, plain, hit.get("syncedLyrics"), "lrclib")
    db.mark_fetched(con, "lyrics", key, bool(hit))
    return get_cached(con, artist, title)


def text_of(row: sqlite3.Row | None) -> str | None:
    if not row:
        return None
    return row["plain"] or (strip_timestamps(row["synced"]) if row["synced"] else None)


_BAD = re.compile(r'[\\/:*?"<>|]')


def ncmpcpp_path(directory: str, artist: str, title: str) -> Path:
    """ncmpcpp's lyrics file name: '<artist> - <title>.txt' with filename-unsafe chars removed."""
    return Path(directory).expanduser() / _BAD.sub("", f"{artist} - {title}.txt")


def export_ncmpcpp(directory: str, song: dict, text: str) -> Path | None:
    if not directory:
        return None
    path = ncmpcpp_path(directory, first(song.get("artist")), first(song.get("title")))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
    return path
