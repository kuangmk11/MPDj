"""Find local files for 'artist + title' pairs from Last.fm."""
from __future__ import annotations

import random

from .names import first, is_live, norm, norm_artist, norm_title


def artist_songs(player, artist: str) -> list[dict]:
    """All library songs by this artist (substring search, then exact-name filter)."""
    want = norm(artist)
    hits = player.search("artist", artist)
    exact = [s for s in hits if norm(first(s.get("artist"))) == want]
    return exact or [s for s in hits if want in norm(first(s.get("artist")))]


def find_track(songs: list[dict], title: str, avoid: set[str] = frozenset(),
               ratings: dict[str, int] | None = None) -> dict | None:
    """Pick the best local copy of `title` among `songs` (one artist's songs).

    Exact normalized title wins over prefix match; studio over live; higher rating first;
    returns None if every copy is in `avoid` (recently played / queued).
    """
    want = norm_title(title)
    if not want:
        return None
    ratings = ratings or {}
    cands = []
    for s in songs:
        t = norm_title(first(s.get("title")))
        if t == want:
            score = 0
        elif t.startswith(want + " ") or (want.startswith(t + " ") and len(t) > 3):
            score = 1
        else:
            continue
        cands.append((s["file"] in avoid, score, is_live(first(s.get("title")), s["file"]),
                      -ratings.get(s["file"], 3), random.random(), s))
    if not cands:
        return None
    cands.sort(key=lambda c: c[:5])
    best = cands[0]
    return None if best[0] else best[5]


def same_artist(a: dict, b: dict, aliases=None) -> bool:
    return norm_artist(first(a.get("artist")), aliases) == norm_artist(first(b.get("artist")), aliases)
