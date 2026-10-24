"""Last.fm client with a DB cache (replaces the wget + xml_grep calls)."""
from __future__ import annotations

import hashlib
import html
import re
import sqlite3

import requests

from . import db
from .config import Config
from .names import norm, norm_artist, norm_title

API = "https://ws.audioscrobbler.com/2.0/"


class LastFMError(Exception):
    pass


class LastFM:
    def __init__(self, cfg: Config, con: sqlite3.Connection, session: requests.Session | None = None):
        self.cfg = cfg
        self.con = con
        self.http = session or requests.Session()
        self.http.headers["User-Agent"] = "mpdj/0.1"
        self.ttl = cfg.cache_days * 86400

    # --- raw calls --------------------------------------------------------
    def call(self, method: str, **params) -> dict:
        if not self.cfg.lastfm_api_key:
            raise LastFMError("no Last.fm api_key in config")
        params.update(method=method, api_key=self.cfg.lastfm_api_key, format="json")
        r = self.http.get(API, params=params, timeout=20)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if "error" in data or r.status_code != 200:
            raise LastFMError(data.get("message") or f"HTTP {r.status_code}")
        return data

    def _sign(self, params: dict) -> str:
        s = "".join(f"{k}{params[k]}" for k in sorted(params) if k != "format")
        return hashlib.md5((s + self.cfg.lastfm_api_secret).encode()).hexdigest()

    def signed_post(self, method: str, **params) -> dict:
        if not self.cfg.lastfm_api_secret:
            raise LastFMError("no Last.fm api_secret in config")
        params.update(method=method, api_key=self.cfg.lastfm_api_key)
        params["api_sig"] = self._sign(params)
        params["format"] = "json"
        r = self.http.post(API, data=params, timeout=20)
        data = r.json()
        if "error" in data:
            raise LastFMError(data.get("message"))
        return data

    # --- cached lookups ---------------------------------------------------
    def _key(self, artist: str) -> str:
        return norm_artist(artist, self.cfg.aliases)

    def similar(self, artist: str, refresh: bool = False) -> list[tuple[str, float]]:
        """[(name, match 0..1)], best first. Falls back to cache if Last.fm is down."""
        key = self._key(artist)
        if refresh or not db.is_fresh(self.con, "similar", key, self.ttl):
            try:
                data = self.call("artist.getSimilar", artist=key, autocorrect=1, limit=100)
                rows = data.get("similarartists", {}).get("artist", [])
                self.con.execute("BEGIN")
                self.con.execute("DELETE FROM similar WHERE artist=?", (key,))
                self.con.executemany(
                    "INSERT OR REPLACE INTO similar(artist,other,other_norm,match) VALUES(?,?,?,?)",
                    [(key, a["name"], norm(a["name"]), float(a.get("match") or 0)) for a in rows],
                )
                self.con.execute("COMMIT")
                db.mark_fetched(self.con, "similar", key, True)
            except (LastFMError, requests.RequestException, ValueError):
                if self.con.in_transaction:
                    self.con.execute("ROLLBACK")
                db.mark_fetched(self.con, "similar", key, False)
        return [(r["other"], r["match"]) for r in self.con.execute(
            "SELECT other, match FROM similar WHERE artist=? ORDER BY match DESC", (key,))]

    def top_tracks(self, artist: str, refresh: bool = False) -> list[str]:
        key = self._key(artist)
        if refresh or not db.is_fresh(self.con, "top", key, self.ttl):
            try:
                data = self.call("artist.getTopTracks", artist=key, autocorrect=1, limit=50)
                rows, seen = [], set()
                for t in data.get("toptracks", {}).get("track", []):
                    if norm_title(t["name"]) not in seen:  # "X" and "X - 2007 Remaster" are one song
                        seen.add(norm_title(t["name"]))
                        rows.append(t)
                self.con.execute("BEGIN")
                self.con.execute("DELETE FROM top_track WHERE artist=?", (key,))
                self.con.executemany(
                    "INSERT OR REPLACE INTO top_track(artist,title,title_norm,rank,playcount) VALUES(?,?,?,?,?)",
                    [(key, t["name"], norm_title(t["name"]), i, int(t.get("playcount") or 0))
                     for i, t in enumerate(rows, 1)],
                )
                self.con.execute("COMMIT")
                db.mark_fetched(self.con, "top", key, True)
            except (LastFMError, requests.RequestException, ValueError):
                if self.con.in_transaction:
                    self.con.execute("ROLLBACK")
                db.mark_fetched(self.con, "top", key, False)
        return [r["title"] for r in self.con.execute(
            "SELECT title FROM top_track WHERE artist=? ORDER BY rank", (key,))]

    def info(self, artist: str, refresh: bool = False) -> dict | None:
        key = self._key(artist)
        if refresh or not db.is_fresh(self.con, "info", key, self.ttl):
            try:
                a = self.call("artist.getInfo", artist=key, autocorrect=1)["artist"]
                bio = clean_bio(a.get("bio", {}).get("content") or "")
                tags = ", ".join(t["name"] for t in a.get("tags", {}).get("tag", []))
                self.con.execute(
                    "INSERT INTO artist(norm,name,bio,tags,url,fetched_at) VALUES(?,?,?,?,?,?) "
                    "ON CONFLICT(norm) DO UPDATE SET name=excluded.name, bio=excluded.bio, "
                    "tags=excluded.tags, url=excluded.url, fetched_at=excluded.fetched_at",
                    (key, a["name"], bio, tags, a.get("url"), db.now()),
                )
                db.mark_fetched(self.con, "info", key, True)
            except (LastFMError, requests.RequestException, ValueError, KeyError):
                db.mark_fetched(self.con, "info", key, False)
        row = self.con.execute("SELECT * FROM artist WHERE norm=?", (key,)).fetchone()
        return dict(row) if row else None

    def loved_tracks(self, user: str) -> list[tuple[str, str]]:
        out, page = [], 1
        while True:
            d = self.call("user.getLovedTracks", user=user, limit=1000, page=page)["lovedtracks"]
            out += [(t["artist"]["name"], t["name"]) for t in d.get("track", [])]
            if page >= int(d["@attr"]["totalPages"]):
                return out
            page += 1

    # --- auth + love ------------------------------------------------------
    def session_key(self) -> str:
        sk = db.get_meta(self.con, "lastfm_session")
        if not sk:
            raise LastFMError("not logged in to Last.fm; run `mpdj lastfm-login`")
        return sk

    def login(self, username: str, password: str) -> None:
        d = self.signed_post("auth.getMobileSession", username=username, password=password)
        db.set_meta(self.con, "lastfm_session", d["session"]["key"])

    def love(self, artist: str, title: str) -> None:
        self.signed_post("track.love", artist=artist, track=title, sk=self.session_key())


def clean_bio(text: str) -> str:
    text = re.sub(r"<a [^>]*>Read more on Last\.fm</a>.*", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()
