"""`mpdj daemon`: waits on MPD events instead of polling.

On every song change: logs history (and skips), skips banned songs, refills the queue with
similar music, and pre-fetches artist info + lyrics in the background.
"""
from __future__ import annotations

import logging
import queue
import threading
import time

from mpd import ConnectionError as MPDConnectionError

from . import autoqueue, db, lyrics, state
from .config import Config
from .lastfm import LastFM
from .names import first
from .player import Player

log = logging.getLogger("mpdj.daemon")
REFILL_COOLDOWN = 20  # seconds between refills for the same song


class Prefetcher(threading.Thread):
    """Background thread with its own DB connection (sqlite objects can't cross threads)."""

    def __init__(self, cfg: Config):
        super().__init__(daemon=True, name="prefetch")
        self.cfg = cfg
        self.jobs: queue.Queue[dict] = queue.Queue()

    def run(self) -> None:
        con = db.connect(self.cfg.db_path)
        lfm = LastFM(self.cfg, con)
        while True:
            song = self.jobs.get()
            artist = first(song.get("artist"))
            try:
                if artist and self.cfg.lastfm_api_key:
                    lfm.info(artist)
                    lfm.similar(artist)
                    lfm.top_tracks(artist)
                text = lyrics.text_of(lyrics.lookup(con, song))
                if text:
                    lyrics.export_ncmpcpp(self.cfg.ncmpcpp_lyrics_dir, song, text)
            except Exception:
                log.exception("prefetch failed for %s", song.get("file"))


class Daemon:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.con = db.connect(cfg.db_path)
        self.lfm = LastFM(cfg, self.con)
        self.prefetch = Prefetcher(cfg)
        # what is playing, as of the last event
        self.song_id: str | None = None
        self.song: dict | None = None
        self.hist_id: int | None = None
        self.elapsed = 0.0
        self.observed_at = 0.0
        self.playing = False
        self.last_refill = 0.0

    def run_forever(self) -> None:
        self.prefetch.start()
        delay = 1
        while True:
            p = Player(self.cfg)
            try:
                p.connect()
                log.info("connected to MPD at %s:%s", self.cfg.mpd_host, self.cfg.mpd_port)
                delay = 1
                self.loop(p)
            except (MPDConnectionError, OSError) as e:
                log.warning("MPD connection lost (%s); retrying in %ss", e, delay)
                # Keep the play record open: an MPD restart is not a skip. Song ids can
                # change on restart, so on_event matches the song by file after reconnecting.
                self.song_id = None
                self.playing = False
                time.sleep(delay)
                delay = min(delay * 2, 60)
            finally:
                p.close()

    def loop(self, p: Player) -> None:
        self.on_event(p, {"player", "playlist"})
        while True:
            changed = set(p.c.idle("player", "playlist", "options"))
            self.on_event(p, changed)

    # --- event handling ---------------------------------------------------
    def on_event(self, p: Player, changed: set[str]) -> None:
        st = p.status()
        now = time.time()
        sid = st.get("songid") if st.get("state") in ("play", "pause") else None
        if sid and self.song_id is None and self.hist_id is not None and self.song:
            cur = p.current()
            if cur and cur.get("file") == self.song.get("file"):
                self.song_id = sid  # same song after a reconnect
        if sid != self.song_id:
            self.close_history(now)
            self.song_id = sid
            self.song = p.current() if sid else None
            if self.song:
                reason = state.BanList(self.con).reason(self.song)
                if reason and st.get("state") == "play":
                    log.info("skipping banned (%s): %s", reason, self.song["file"])
                    self.song_id = None
                    p.next()
                    return  # the skip fires another event
                self.hist_id = state.start_play(self.con, self.song)
                self.prefetch.jobs.put(self.song)
                log.info("now playing: %s - %s", first(self.song.get("artist")), first(self.song.get("title")))
            self.last_refill = 0
        self.elapsed = float(st.get("elapsed", 0) or 0)
        self.observed_at = now
        self.playing = st.get("state") == "play"

        if self.song and (now - self.last_refill) > REFILL_COOLDOWN and autoqueue.needs_refill(p, self.cfg):
            self.last_refill = now
            self.refill(p)

    def close_history(self, now: float | None = None) -> None:
        if self.hist_id is None:
            return
        now = now or time.time()
        played = self.elapsed + ((now - self.observed_at) if self.playing else 0)
        dur = self.song.get("duration") or self.song.get("time") if self.song else None
        skipped = state.end_play(self.con, self.hist_id, played, self.cfg.min_play_seconds,
                                 float(dur) if dur else None)
        if skipped and self.song:
            log.info("skip logged: %s", self.song["file"])
        self.hist_id = None

    def refill(self, p: Player) -> None:
        picker = autoqueue.Picker(p, self.con, self.lfm, self.cfg)
        songs = picker.similar_mix(self.song, self.cfg.batch)
        for s in songs:
            p.add(s["file"])
        log.info("queued %d: %s", len(songs),
                 ", ".join(first(s.get("artist")) for s in songs) or "nothing found")


def main(cfg: Config) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("mpd").setLevel(logging.WARNING)
    Daemon(cfg).run_forever()
