"""Pick songs to keep the queue going (replaces similar-artists-new / lfm-plex)."""
from __future__ import annotations

import random

from . import state
from .names import first, norm, norm_artist

HUB_MIN_SEEDS = 10  # need this many cached similar lists before hub counts mean anything
HUB_FLOOR = 0.1     # an artist on every list keeps (0.1)^2 = 1% of its weight


class Picker:
    """Collects everything needed to filter songs once, then picks many."""

    def __init__(self, player, con, lfm, cfg, rng: random.Random | None = None):
        self.p, self.con, self.lfm, self.cfg = player, con, lfm, cfg
        self.rng = rng or random.Random()
        self.bans = state.BanList(con)
        self.ratings = state.ratings(con)
        self.recent = state.recently_played(con, cfg.recent_days)
        self.taken = {s["file"] for s in player.queue()}
        self._library_artists: dict[str, str] | None = None
        self._hubs: dict[str, float] | None = None

    # --- filters ----------------------------------------------------------
    def ok(self, song: dict) -> bool:
        f = song["file"]
        return (f not in self.taken and f not in self.recent
                and self.ratings.get(f, 3) >= 3 and song not in self.bans)

    def library_artists(self) -> dict[str, str]:
        """norm(artist) -> artist name as tagged in the library."""
        if self._library_artists is None:
            self._library_artists = {}
            for a in self.p.list_artists():
                self._library_artists.setdefault(norm(a), a)
        return self._library_artists

    def songs_by(self, artist: str) -> list[dict]:
        from .match import artist_songs
        return [s for s in artist_songs(self.p, artist) if self.ok(s)]

    def pick_song(self, songs: list[dict]) -> dict | None:
        if not songs:
            return None
        # Songs rated 4-5 are three times as likely.
        weights = [3 if self.ratings.get(s["file"], 3) >= 4 else 1 for s in songs]
        return self.rng.choices(songs, weights)[0]

    def take(self, song: dict) -> dict:
        self.taken.add(song["file"])
        return song

    # --- strategies -------------------------------------------------------
    def hub_penalty(self) -> dict[str, float]:
        """norm(artist) -> weight multiplier. Artists that turn up on many of the cached
        similar lists (OMD, Howard Jones, ABC...) are generic hubs; picking them by match
        alone pulls every mix toward them."""
        if self._hubs is None:
            self._hubs = {}
            seeds = self.con.execute("SELECT COUNT(DISTINCT artist) FROM similar").fetchone()[0]
            if seeds >= HUB_MIN_SEEDS:
                for r in self.con.execute("SELECT other_norm, COUNT(*) FROM similar GROUP BY other_norm"):
                    frac = r[1] / seeds
                    self._hubs[r[0]] = max(HUB_FLOOR, 1 - frac) ** 2
        return self._hubs

    def similar_pool(self, artist: str) -> list[tuple[str, float]]:
        """Similar artists that exist in the library: [(library name, weight)]."""
        lib = self.library_artists()
        hubs = self.hub_penalty()
        seed = norm_artist(artist, self.cfg.aliases)
        pool = []
        for name, match in self.lfm.similar(artist):
            n = norm(name)
            if n in lib and n != seed:
                pool.append((lib[n], max(match, 0.05) * hubs.get(n, 1.0)))
        return pool

    def similar_mix(self, seed: dict, n: int, current: dict | None = None) -> list[dict]:
        """n songs: the seed's similar artists weighted by Last.fm match (minus the hub
        penalty), with the seed artist itself about 1 in `same_artist_every` picks, never
        the same artist twice in a row. `current` is what's playing, if not the seed."""
        artist = first(seed.get("artist"))
        seed_norm = norm(artist)
        pool = dict(self.similar_pool(artist)) if artist else {}
        songs: dict[str, list[dict]] = {}

        def usable(name: str) -> list[dict]:
            if name not in songs:
                songs[name] = self.songs_by(name)
            return [s for s in songs[name] if s["file"] not in self.taken]

        out: list[dict] = []
        # don't follow what's playing with the same artist
        last = norm(first((current or seed).get("artist")))
        seed_left = bool(artist)
        every = max(self.cfg.same_artist_every, 1)
        while len(out) < n and (pool or seed_left):
            want_seed = seed_left and last != seed_norm and (not pool or (len(out) + 1) % every == 0)
            if want_seed:
                name = artist
            else:
                choices = [(a, w) for a, w in pool.items() if norm(a) != last]
                if not choices:
                    if seed_left and last != seed_norm:
                        name = artist
                    else:
                        break
                else:
                    names, weights = zip(*choices)
                    name = self.rng.choices(names, weights)[0]
            song = self.pick_song(usable(name))
            if song is None:  # this artist is used up
                if name == artist:
                    seed_left = False
                pool.pop(name, None)
                continue
            out.append(self.take(song))
            last = norm(name)
        if len(out) < n:
            out += self.genre_fill(seed, n - len(out), current)
        return out

    def genre_fill(self, seed: dict, n: int, current: dict | None = None) -> list[dict]:
        genre = first(seed.get("genre"))
        if not genre or n <= 0:
            return []
        songs = [s for s in self.p.search("genre", genre) if self.ok(s)]
        self.rng.shuffle(songs)
        out, last = [], norm(first((current or seed).get("artist")))
        for s in songs:
            a = norm(first(s.get("artist")))
            if a != last and s["file"] not in self.taken:
                out.append(self.take(s))
                last = a
                if len(out) >= n:
                    break
        return out

    def top_tracks(self, seed: dict, n: int) -> list[dict]:
        """Up to n of the artist's Last.fm top tracks that exist locally, in rank order."""
        from .match import find_track
        artist = first(seed.get("artist"))
        songs = [s for s in self.songs_by(artist)] if artist else []
        avoid = self.taken | self.recent
        out = []
        for title in self.lfm.top_tracks(artist):
            if title and norm(title) == norm(first(seed.get("title"))):
                continue
            s = find_track(songs, title, avoid=avoid, ratings=self.ratings)
            if s:
                out.append(self.take(s))
                avoid.add(s["file"])
                if len(out) >= n:
                    break
        return out


def needs_refill(player, cfg) -> bool:
    st = player.status()
    if cfg.require_consume and st.get("consume") != "1":
        return False
    return player.songs_after_current() < cfg.min_ahead
