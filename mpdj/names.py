"""Name cleanup. Replaces the sed chains in the old `variables` file."""
from __future__ import annotations

import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")
_SUFFIX = re.compile(r"\s+-\s+[^-]*\b(remaster(ed)?|version|mix|edit|live|mono|stereo|demo|single)\b.*$", re.I)
_LIVE = re.compile(r"[\(\[]\s*live\b|\blive (at|in|from)\b", re.I)


def strip_brackets(s: str) -> str:
    """Drop everything inside () and [], nested or unclosed: 'Song [Live (Demo)]' -> 'Song'."""
    out, depth = [], 0
    for c in s:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth = max(depth - 1, 0)
        elif depth == 0:
            out.append(c)
    return _SPACES.sub(" ", "".join(out)).strip()


def fold(s: str) -> str:
    """Strip accents: 'Crêche' -> 'Creche'."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str | None, drop_brackets: bool = False) -> str:
    """Comparison key: lowercase, no accents, '&' -> 'and', no punctuation, single spaces.

    norm("Siouxsie & The Banshees") == norm("siouxsie and the banshees")
    """
    if not s:
        return ""
    s = fold(s).lower().replace("&", " and ")
    if drop_brackets:
        s = _SUFFIX.sub("", strip_brackets(s)) or s  # '[Untitled]' keeps its name
    s = s.replace("'", "").replace("’", "")
    s = _PUNCT.sub(" ", s)
    return _SPACES.sub(" ", s).strip()


def norm_title(s: str | None) -> str:
    """Track title key; ignores '(Remastered)', '[Live]' etc. like the old _TITLE did."""
    return norm(s, drop_brackets=True)


def norm_artist(s: str | None, aliases: dict[str, str] | None = None) -> str:
    """Artist key with alias mapping (e.g. warsaw -> joy division).

    Alias keys ending in '*' match by prefix: {"christian death*": "christian death"}.
    """
    n = norm(s)
    for k, v in (aliases or {}).items():
        if k.endswith("*"):
            if n.startswith(norm(k[:-1])):
                return norm(v)
        elif n == norm(k):
            return norm(v)
    return n


def is_live(title: str | None, file: str | None = None) -> bool:
    return bool(_LIVE.search(title or "") or _LIVE.search(file or ""))


def first(v):
    """MPD returns a list when a tag appears more than once; take the first."""
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""
