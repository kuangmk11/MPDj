"""Thin wrapper over python-mpd2 so the rest of the code talks in plain dicts."""
from __future__ import annotations

from contextlib import contextmanager

from mpd import CommandError, MPDClient

from .config import Config
from .names import first


class Player:
    def __init__(self, cfg: Config, client: MPDClient | None = None):
        self.cfg = cfg
        self.c = client or MPDClient()
        self._own = client is None

    # --- connection -------------------------------------------------------
    def connect(self) -> "Player":
        if self._own:
            self.c.timeout = 30
            self.c.idletimeout = None
            self.c.connect(self.cfg.mpd_host, self.cfg.mpd_port)
            if self.cfg.mpd_password:
                self.c.password(self.cfg.mpd_password)
        return self

    def close(self) -> None:
        if self._own:
            try:
                self.c.close()
                self.c.disconnect()
            except Exception:
                pass

    # --- reading state ----------------------------------------------------
    def status(self) -> dict:
        return self.c.status()

    def current(self) -> dict | None:
        song = self.c.currentsong()
        return song or None

    def queue(self) -> list[dict]:
        return self.c.playlistinfo()

    def next_song(self) -> dict | None:
        """The song that will play after this one (None at the end of the queue)."""
        st = self.status()
        if "nextsong" in st:
            pos = int(st["nextsong"])
        elif "song" in st:
            pos = int(st["song"]) + 1
        else:
            return None
        if pos >= int(st.get("playlistlength", 0)):
            return None
        found = self.c.playlistinfo(pos)
        return found[0] if found else None

    def songs_after_current(self) -> int:
        st = self.status()
        length = int(st.get("playlistlength", 0))
        pos = int(st["song"]) if "song" in st else -1
        return length - pos - 1

    def search(self, *pairs: str, exact: bool = False) -> list[dict]:
        """search('artist', 'Joy Division', 'title', 'Disorder'). Substring, case-insensitive
        unless exact=True."""
        return (self.c.find if exact else self.c.search)(*pairs)

    def list_artists(self) -> list[str]:
        out = self.c.list("artist")
        # python-mpd2 >= 3 returns [{'artist': ...}]
        return [first(a["artist"]) if isinstance(a, dict) else a for a in out if a]

    # --- changing the queue ----------------------------------------------
    def add(self, file: str) -> None:
        self.c.add(file)

    def insert_next(self, file: str) -> None:
        """Insert right after the current song (like `mpc insert`)."""
        st = self.status()
        if "song" in st:
            self.c.addid(file, int(st["song"]) + 1)
        else:
            self.c.add(file)

    def crop(self) -> None:
        """Remove everything except the current song (like `mpc crop`)."""
        st = self.status()
        if "song" not in st:
            return
        cur = int(st["song"])
        length = int(st.get("playlistlength", 0))
        if cur + 1 < length:
            self.c.delete((cur + 1, length))
        if cur > 0:
            self.c.delete((0, cur))

    def delete_pos(self, pos: int) -> None:
        self.c.delete(pos)

    def move(self, frm, to: int) -> None:
        self.c.move(frm, to)

    def play(self, pos: int | None = None) -> None:
        if pos is None:
            self.c.play()
        else:
            self.c.play(pos)

    def next(self) -> None:
        self.c.next()

    def ensure_playing(self) -> None:
        if self.status().get("state") != "play":
            self.c.play()

    # --- stickers (so other MPD clients can see ratings) -----------------
    def set_sticker(self, file: str, name: str, value: str) -> None:
        try:
            self.c.sticker_set("song", file, name, value)
        except CommandError:
            pass  # sticker_file not configured in mpd.conf; the DB still has it

    # --- stored playlists -------------------------------------------------
    def playlist_add(self, name: str, file: str) -> None:
        self.c.playlistadd(name, file)

    def playlist_clear(self, name: str) -> None:
        try:
            self.c.playlistclear(name)
        except CommandError:
            pass

    def playlist_files(self, name: str) -> list[str]:
        try:
            return self.c.listplaylist(name)
        except CommandError:
            return []


@contextmanager
def connected(cfg: Config):
    p = Player(cfg).connect()
    try:
        yield p
    finally:
        p.close()
