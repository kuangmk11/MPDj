"""SQLite store. Replaces the _lyrics, __similar, __top100, __suggestions dirs,
~/.PLAYED, ~/.mpdskip/*.txt and the rating tags/stickers."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS artist (
    norm TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    bio TEXT,
    tags TEXT,
    url TEXT,
    fetched_at REAL
);
CREATE TABLE IF NOT EXISTS similar (
    artist TEXT NOT NULL,          -- norm of source artist
    other TEXT NOT NULL,           -- display name of similar artist
    other_norm TEXT NOT NULL,
    match REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (artist, other_norm)
);
CREATE TABLE IF NOT EXISTS top_track (
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL,
    rank INTEGER NOT NULL,
    playcount INTEGER,
    PRIMARY KEY (artist, title_norm)
);
CREATE TABLE IF NOT EXISTS fetch_log (     -- cache freshness per (kind, key)
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    ok INTEGER NOT NULL,
    PRIMARY KEY (kind, key)
);
CREATE TABLE IF NOT EXISTS lyrics (
    artist TEXT NOT NULL,          -- norm
    title TEXT NOT NULL,           -- norm_title
    plain TEXT,
    synced TEXT,
    source TEXT,
    fetched_at REAL,
    PRIMARY KEY (artist, title)
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY,
    file TEXT NOT NULL,
    artist TEXT,
    title TEXT,
    started_at REAL NOT NULL,
    seconds REAL,
    skipped INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS history_file ON history(file);
CREATE INDEX IF NOT EXISTS history_time ON history(started_at);
CREATE TABLE IF NOT EXISTS rating (
    file TEXT PRIMARY KEY,
    stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
    rated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS ban (
    kind TEXT NOT NULL CHECK (kind IN ('artist','album','genre','dir','song','string')),
    value TEXT NOT NULL,           -- norm for artist/album/genre, raw path for dir/song, lowercase for string
    expires_at REAL,               -- NULL = permanent
    created_at REAL NOT NULL,
    PRIMARY KEY (kind, value)
);
CREATE TABLE IF NOT EXISTS suggest_ignore (
    norm TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10, isolation_level=None)  # autocommit
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def now() -> float:
    return time.time()


def is_fresh(con: sqlite3.Connection, kind: str, key: str, max_age_s: float) -> bool:
    row = con.execute("SELECT fetched_at, ok FROM fetch_log WHERE kind=? AND key=?", (kind, key)).fetchone()
    # Failed fetches are retried after an hour rather than the full TTL.
    age = max_age_s if (row and row["ok"]) else 3600
    return bool(row) and (now() - row["fetched_at"]) < age


def mark_fetched(con: sqlite3.Connection, kind: str, key: str, ok: bool) -> None:
    con.execute(
        "INSERT INTO fetch_log(kind,key,fetched_at,ok) VALUES(?,?,?,?) "
        "ON CONFLICT(kind,key) DO UPDATE SET fetched_at=excluded.fetched_at, ok=excluded.ok",
        (kind, key, now(), int(ok)),
    )


def get_meta(con, k, default=None):
    row = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return row["v"] if row else default


def set_meta(con, k, v):
    con.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
