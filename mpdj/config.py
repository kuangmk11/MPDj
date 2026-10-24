"""Settings, read from ~/.config/mpdj/config.toml (all keys optional)."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mpdj"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "mpdj"
CONFIG_FILE = Path(os.environ.get("MPDJ_CONFIG", CONFIG_DIR / "config.toml"))

EXAMPLE = """\
# mpdj settings. Everything is optional; these are the defaults.

[mpd]
host = "localhost"
port = 6600
password = ""
# Same path as music_directory in mpd.conf. Needed for tag reading and the legacy import.
music_dir = ""

[lastfm]
api_key = ""
api_secret = ""      # only needed for loving tracks (rate 5)
username = ""        # only needed for `loved sync` and loving tracks
cache_days = 7

[autoqueue]
min_ahead = 10       # refill when fewer songs than this are left after the current one
batch = 10           # how many to add per refill
same_artist_every = 3  # roughly 1 in N picks is the current artist
recent_days = 14     # don't re-add songs played in the last N days
require_consume = true # only refill when MPD consume mode is on (old behaviour)

[skip]
min_play_seconds = 30  # leaving a song earlier than this counts as a skip

[lyrics]
# ncmpcpp reads "<artist> - <title>.txt" from here. Leave blank to not export.
ncmpcpp_dir = "~/.lyrics"

[aliases]
# Artist names to treat as another artist when asking Last.fm.
"warsaw" = "joy division"
"christian death*" = "christian death"   # * = prefix match

[suggest]
links = [
  ["Last.fm", "https://www.last.fm/music/{q}"],
  ["Bandcamp", "https://bandcamp.com/search?q={q}"],
  ["Google", "https://www.google.com/search?q={q}"],
]
"""


@dataclass
class Config:
    mpd_host: str = "localhost"
    mpd_port: int = 6600
    mpd_password: str = ""
    music_dir: str = ""
    lastfm_api_key: str = ""
    lastfm_api_secret: str = ""
    lastfm_username: str = ""
    cache_days: int = 7
    min_ahead: int = 10
    batch: int = 10
    same_artist_every: int = 3
    recent_days: int = 14
    require_consume: bool = True
    min_play_seconds: int = 30
    ncmpcpp_lyrics_dir: str = "~/.lyrics"
    aliases: dict[str, str] = field(default_factory=lambda: {
        "warsaw": "joy division", "christian death*": "christian death"})
    suggest_links: list[list[str]] = field(default_factory=lambda: [
        ["Last.fm", "https://www.last.fm/music/{q}"],
        ["Bandcamp", "https://bandcamp.com/search?q={q}"],
        ["Google", "https://www.google.com/search?q={q}"],
    ])
    db_path: Path = DATA_DIR / "mpdj.db"


def load(path: Path = CONFIG_FILE) -> Config:
    cfg = Config()
    if path.exists():
        raw = tomllib.loads(path.read_text())
        m, lf, aq = raw.get("mpd", {}), raw.get("lastfm", {}), raw.get("autoqueue", {})
        cfg.mpd_host = m.get("host", cfg.mpd_host)
        cfg.mpd_port = int(m.get("port", cfg.mpd_port))
        cfg.mpd_password = m.get("password", cfg.mpd_password)
        cfg.music_dir = m.get("music_dir", cfg.music_dir)
        cfg.lastfm_api_key = lf.get("api_key", cfg.lastfm_api_key)
        cfg.lastfm_api_secret = lf.get("api_secret", cfg.lastfm_api_secret)
        cfg.lastfm_username = lf.get("username", cfg.lastfm_username)
        cfg.cache_days = int(lf.get("cache_days", cfg.cache_days))
        for k in ("min_ahead", "batch", "same_artist_every", "recent_days"):
            setattr(cfg, k, int(aq.get(k, getattr(cfg, k))))
        cfg.require_consume = bool(aq.get("require_consume", cfg.require_consume))
        cfg.min_play_seconds = int(raw.get("skip", {}).get("min_play_seconds", cfg.min_play_seconds))
        cfg.ncmpcpp_lyrics_dir = raw.get("lyrics", {}).get("ncmpcpp_dir", cfg.ncmpcpp_lyrics_dir)
        if "aliases" in raw:
            cfg.aliases = {k.lower(): v.lower() for k, v in raw["aliases"].items()}
        cfg.suggest_links = raw.get("suggest", {}).get("links", cfg.suggest_links)
    # Environment overrides, handy for secrets.
    cfg.mpd_host = os.environ.get("MPD_HOST", cfg.mpd_host)
    cfg.mpd_port = int(os.environ.get("MPD_PORT", cfg.mpd_port))
    cfg.lastfm_api_key = os.environ.get("LASTFM_API_KEY", cfg.lastfm_api_key)
    if "MPDJ_DB" in os.environ:
        cfg.db_path = Path(os.environ["MPDJ_DB"])
    return cfg


def write_example(path: Path = CONFIG_FILE) -> bool:
    """Create a starter config if none exists. Returns True if written."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EXAMPLE)
    path.chmod(0o600)
    return True
