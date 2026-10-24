"""Lyrics from LRCLIB (free, no key, often time-synced), then lyrics.ovh; cached in the DB."""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote

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


HEADERS = {"User-Agent": "mpdj/0.1 (personal MPD helper)"}
_RETRY = (429, 500, 502, 503, 504)
_EXTRA = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]|\s+-\s+[^-]*\b(remaster(ed)?|version|mix|edit|live|mono|stereo|demo|single)\b.*$", re.I)


class Busy(requests.RequestException):
    """The lyrics site kept answering 'try again later'. Not a miss, so don't cache it."""


def clean_title(title: str) -> str:
    """'Kameradschaft [Live]' -> 'Kameradschaft' (what lyrics sites file songs under)."""
    return _EXTRA.sub("", title).strip() or title


def _get(http: requests.Session, url: str, params: dict | None = None, tries: int = 3) -> requests.Response:
    for i in range(tries):
        r = http.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code not in _RETRY:
            return r
        time.sleep(2 * (i + 1))
    raise Busy(f"{url}: HTTP {r.status_code}")


def _usable(hit: dict) -> bool:
    return bool(hit.get("plainLyrics") or hit.get("syncedLyrics") or hit.get("instrumental"))


def fetch_lrclib(artist: str, title: str, album: str = "", duration: float | None = None,
                 http: requests.Session | None = None) -> dict | None:
    http = http or requests.Session()
    clean = clean_title(title)
    params = {"artist_name": artist, "track_name": clean}
    if album:
        params["album_name"] = album
    if duration:
        params["duration"] = int(round(duration))
    r = _get(http, f"{LRCLIB}/get", params)
    if r.status_code == 200 and _usable(r.json()):
        return r.json()
    # Album/duration often differ from LRCLIB's copy, and tags differ in spelling
    # ('Junglinge' vs 'Jünglinge'), so search and compare normalized names.
    want_a, want_t = norm(artist), norm_title(title)
    for q in ({"artist_name": artist, "track_name": clean}, {"q": f"{artist} {clean}"}):
        r = _get(http, f"{LRCLIB}/search", q)
        if r.status_code != 200:
            continue
        hits = [h for h in r.json() if norm(h.get("artistName")) == want_a
                and norm_title(h.get("trackName")) == want_t and _usable(h)]
        if hits:
            # prefer the copy closest in length to ours, then one with synced lyrics
            hits.sort(key=lambda h: (abs((h.get("duration") or 0) - (duration or 0)) if duration else 0,
                                     not h.get("syncedLyrics")))
            return hits[0]
    return None


def fetch_lyrics_ovh(artist: str, title: str, http: requests.Session | None = None) -> str | None:
    """api.lyrics.ovh: free, no key; plain text only. Has some songs LRCLIB lacks."""
    http = http or requests.Session()
    url = f"https://api.lyrics.ovh/v1/{quote(artist, safe='')}/{quote(clean_title(title), safe='')}"
    try:
        r = _get(http, url, tries=2)
    except Busy:
        return None
    if r.status_code != 200:
        return None
    text = (r.json().get("lyrics") or "").replace("\r\n", "\n").strip()
    # it sometimes prefixes "Paroles de la chanson X par Y"
    text = re.sub(r"^Paroles de la chanson .*\n", "", text).strip()
    return text or None


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
    dur = song.get("duration") or song.get("time")
    try:
        hit = fetch_lrclib(artist, title, first(song.get("album")), float(dur) if dur else None)
        busy = False
    except (requests.RequestException, ValueError):
        hit, busy = None, True  # down or overloaded: try the next source, don't cache a miss
    if hit:
        plain = "[instrumental]" if hit.get("instrumental") else hit.get("plainLyrics")
        save(con, artist, title, plain, hit.get("syncedLyrics"), "lrclib")
    else:
        try:
            text = fetch_lyrics_ovh(artist, title)
        except (requests.RequestException, ValueError):
            text, busy = None, True
        if text:
            save(con, artist, title, text, None, "lyrics.ovh")
            hit = True
    if hit or not busy:
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
