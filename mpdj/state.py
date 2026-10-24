"""Ratings, bans and play history (replaces mpdskipper's text lists and ~/.PLAYED)."""
from __future__ import annotations

import json
import os
import sqlite3

from . import db
from .names import first, norm

BAN_KINDS = ("artist", "album", "genre", "dir", "song", "string")
TEMP_BAN_SECONDS = 7 * 86400


# --- bans ------------------------------------------------------------------
def ban_value(kind: str, song: dict | None = None, value: str | None = None) -> str:
    """The stored value for a ban, from the current song or an explicit value."""
    if value is None:
        if song is None:
            raise ValueError("nothing playing")
        value = {
            "artist": first(song.get("artist")),
            "album": first(song.get("album")),
            "genre": first(song.get("genre")),
            "dir": os.path.dirname(song["file"]),
            "song": song["file"],
            "string": "",
        }[kind]
    if kind in ("artist", "album", "genre"):
        return norm(value)
    if kind == "string":
        return value.lower()
    return value.rstrip("/")


def add_ban(con: sqlite3.Connection, kind: str, value: str, temp: bool = False) -> None:
    if not value:
        raise ValueError(f"empty {kind}")
    con.execute(
        "INSERT INTO ban(kind,value,expires_at,created_at) VALUES(?,?,?,?) "
        "ON CONFLICT(kind,value) DO UPDATE SET expires_at=excluded.expires_at, created_at=excluded.created_at",
        (kind, value, db.now() + TEMP_BAN_SECONDS if temp else None, db.now()),
    )


def remove_ban(con: sqlite3.Connection, kind: str, value: str) -> int:
    return con.execute("DELETE FROM ban WHERE kind=? AND value=?", (kind, value)).rowcount


def active_bans(con: sqlite3.Connection) -> list[sqlite3.Row]:
    con.execute("DELETE FROM ban WHERE expires_at IS NOT NULL AND expires_at < ?", (db.now(),))
    return con.execute("SELECT * FROM ban ORDER BY kind, value").fetchall()


class BanList:
    """Loaded once, then checked against many songs quickly."""

    def __init__(self, con: sqlite3.Connection):
        self.by_kind: dict[str, set[str]] = {k: set() for k in BAN_KINDS}
        for r in active_bans(con):
            self.by_kind[r["kind"]].add(r["value"])

    def reason(self, song: dict) -> str | None:
        b = self.by_kind
        f = song.get("file", "")
        if f in b["song"]:
            return "song"
        if norm(first(song.get("artist"))) in b["artist"]:
            return "artist"
        if song.get("album") and norm(first(song.get("album"))) in b["album"]:
            return "album"
        if song.get("genre") and norm(first(song.get("genre"))) in b["genre"]:
            return "genre"
        if any(f.startswith(d + "/") for d in b["dir"]):
            return "dir"
        fl = f.lower()
        if any(s in fl for s in b["string"]):
            return "string"
        return None

    def __contains__(self, song: dict) -> bool:
        return self.reason(song) is not None


# --- ratings ---------------------------------------------------------------
def set_rating(con: sqlite3.Connection, file: str, stars: int) -> None:
    con.execute(
        "INSERT INTO rating(file,stars,rated_at) VALUES(?,?,?) "
        "ON CONFLICT(file) DO UPDATE SET stars=excluded.stars, rated_at=excluded.rated_at",
        (file, stars, db.now()),
    )


def ratings(con: sqlite3.Connection) -> dict[str, int]:
    return {r["file"]: r["stars"] for r in con.execute("SELECT file, stars FROM rating")}


# --- history ---------------------------------------------------------------
def start_play(con: sqlite3.Connection, song: dict) -> int:
    cur = con.execute(
        "INSERT INTO history(file,artist,title,started_at) VALUES(?,?,?,?)",
        (song["file"], first(song.get("artist")), first(song.get("title")), db.now()),
    )
    return cur.lastrowid


def end_play(con: sqlite3.Connection, hist_id: int, seconds: float, min_play: float, duration: float | None) -> bool:
    """Close a history row. A skip = left before min_play seconds and before the song ended."""
    skipped = seconds < min_play and not (duration and seconds >= duration - 2)
    con.execute("UPDATE history SET seconds=?, skipped=? WHERE id=?", (seconds, int(skipped), hist_id))
    return skipped


def recently_played(con: sqlite3.Connection, days: float) -> set[str]:
    since = db.now() - days * 86400
    return {r["file"] for r in con.execute("SELECT DISTINCT file FROM history WHERE started_at >= ?", (since,))}


# --- auto-DJ seed ------------------------------------------------------------
# Refills are built from the last song *you* picked (the anchor), not from the song
# playing now. Seeding from auto-picked songs makes a random walk that drifts to the
# most generic, best-connected artists.
def mark_autoqueued(con: sqlite3.Connection, files) -> None:
    t = db.now()
    con.execute("DELETE FROM autoqueued WHERE added_at < ?", (t - 30 * 86400,))
    con.executemany("INSERT OR REPLACE INTO autoqueued(file,added_at) VALUES(?,?)",
                    [(f, t) for f in files])


def was_autoqueued(con: sqlite3.Connection, file: str) -> bool:
    return con.execute("SELECT 1 FROM autoqueued WHERE file=?", (file,)).fetchone() is not None


def forget_autoqueued(con: sqlite3.Connection, file: str) -> None:
    """Called when the song is done, so a later replay you queue yourself counts as yours.
    (Not at start: a daemon restart mid-song would then take it for your pick.)"""
    con.execute("DELETE FROM autoqueued WHERE file=?", (file,))


def set_anchor(con: sqlite3.Connection, song: dict) -> None:
    keep = {k: song[k] for k in ("file", "artist", "title", "album", "genre") if song.get(k)}
    db.set_meta(con, "anchor", json.dumps(keep))


def anchor(con: sqlite3.Connection) -> dict | None:
    v = db.get_meta(con, "anchor")
    return json.loads(v) if v else None
