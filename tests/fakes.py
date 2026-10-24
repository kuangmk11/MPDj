"""In-memory stand-ins for MPD and Last.fm."""
from __future__ import annotations

import random


def song(artist, title, album="Album", track=1, genre="Darkwave", file=None):
    return {
        "artist": artist, "title": title, "album": album, "track": str(track), "genre": genre,
        "file": file or f"{artist}/{album}/{track:02d} {title}.mp3", "duration": "200",
    }


class FakeMPD:
    def __init__(self, library):
        self.library = list(library)
        self.q: list[dict] = []
        self.pos: int | None = None
        self.state = "stop"
        self.consume = "1"
        self.stickers = {}
        self.playlists: dict[str, list[str]] = {}
        self._next_id = 1

    # status
    def status(self):
        st = {"state": self.state, "playlistlength": str(len(self.q)), "consume": self.consume, "random": "0"}
        if self.pos is not None and self.q:
            st.update(song=str(self.pos), songid=self.q[self.pos]["id"], elapsed="12.0")
        return st

    def currentsong(self):
        return dict(self.q[self.pos]) if self.pos is not None and self.q else {}

    def playlistinfo(self):
        return [dict(s, pos=str(i)) for i, s in enumerate(self.q)]

    # search
    def search(self, *pairs):
        return self._match(pairs, lambda have, want: want.lower() in have.lower())

    def find(self, *pairs):
        return self._match(pairs, lambda have, want: have == want)

    def _match(self, pairs, test):
        crit = list(zip(pairs[::2], pairs[1::2]))
        out = []
        for s in self.library:
            if all(test(s.get(t, "") if t != "any" else " ".join(s.values()), v) for t, v in crit):
                out.append(dict(s))
        return out

    def list(self, tag):
        return [{tag: a} for a in sorted({s[tag] for s in self.library})]

    # queue
    def _entry(self, file):
        s = next(x for x in self.library if x["file"] == file)
        e = dict(s, id=str(self._next_id))
        self._next_id += 1
        return e

    def add(self, file):
        self.q.append(self._entry(file))

    def addid(self, file, pos):
        self.q.insert(pos, self._entry(file))

    def delete(self, rng):
        if isinstance(rng, tuple):
            a, b = rng
        else:
            a, b = rng, rng + 1
        cur = self.q[self.pos] if self.pos is not None else None
        del self.q[a:b]
        self.pos = next((i for i, s in enumerate(self.q) if s is cur), None) if cur else None

    def deleteid(self, sid):
        cur = self.q[self.pos] if self.pos is not None else None
        self.q = [s for s in self.q if s["id"] != str(sid)]
        self.pos = next((i for i, s in enumerate(self.q) if s is cur), None) if cur else None

    def clear(self):
        self.q, self.pos, self.state = [], None, "stop"

    def shuffle(self, rng=None):
        a, b = rng if rng else (0, len(self.q))
        part = self.q[a:b]
        random.shuffle(part)
        self.q[a:b] = part

    def play(self, pos=None):
        self.pos = 0 if pos is None and self.pos is None else (self.pos if pos is None else pos)
        self.state = "play"

    def next(self):
        if self.pos is not None and self.pos + 1 < len(self.q):
            self.pos += 1
        else:
            self.pos, self.state = None, "stop"

    # misc
    def sticker_set(self, kind, file, name, value):
        self.stickers[(file, name)] = value

    def playlistadd(self, name, file):
        self.playlists.setdefault(name, []).append(file)

    def playlistclear(self, name):
        self.playlists[name] = []

    def listplaylist(self, name):
        return list(self.playlists.get(name, []))


class FakeLastFM:
    def __init__(self, similar=None, top=None):
        self._similar = similar or {}
        self._top = top or {}
        self.loved = []

    def similar(self, artist, refresh=False):
        return self._similar.get(artist.lower(), [])

    def top_tracks(self, artist, refresh=False):
        return self._top.get(artist.lower(), [])

    def love(self, artist, title):
        self.loved.append((artist, title))
