import random

from mpdj import db, state
from mpdj.config import Config
from mpdj.daemon import Daemon
from mpdj.player import Player

from .fakes import FakeLastFM, FakeMPD
from .test_core import LIB, SIMILAR


class NoPrefetch:
    def __init__(self):
        self.jobs = []

    def put(self, s, attempt=0):
        self.jobs.append(s)


def make(tmp_path):
    cfg = Config()
    cfg.db_path = tmp_path / "t.db"
    cfg.lastfm_api_key = ""
    d = Daemon(cfg)
    d.lfm = FakeLastFM(SIMILAR)
    d.prefetch = NoPrefetch()
    mpd = FakeMPD(LIB)
    return d, mpd, Player(cfg, client=mpd)


def test_refills_when_queue_short(tmp_path):
    random.seed(0)
    d, mpd, p = make(tmp_path)
    mpd.add(LIB[0]["file"])
    mpd.play(0)
    d.on_event(p, {"player"})
    assert len(mpd.q) == 1 + d.cfg.batch
    assert d.prefetch.jobs[0]["file"] == LIB[0]["file"]
    # a second event right away doesn't refill again (cooldown + enough queued)
    d.on_event(p, {"playlist"})
    assert len(mpd.q) == 1 + d.cfg.batch


def test_skips_banned_and_logs_history(tmp_path):
    d, mpd, p = make(tmp_path)
    mpd.consume = "0"  # no auto-queue in this test
    for s in LIB[:3]:
        mpd.add(s["file"])
    state.add_ban(d.con, "song", LIB[1]["file"])
    mpd.play(0)
    d.on_event(p, {"player"})
    d.elapsed, d.observed_at = 3, 0  # pretend we left after 3 seconds, while paused
    d.playing = False
    mpd.next()                       # -> banned song
    d.on_event(p, {"player"})        # daemon skips it
    assert mpd.q[mpd.pos]["file"] == LIB[2]["file"]
    d.on_event(p, {"player"})
    rows = d.con.execute("SELECT file, skipped FROM history ORDER BY id").fetchall()
    assert [(r["file"], r["skipped"]) for r in rows] == [(LIB[0]["file"], 1), (LIB[2]["file"], 0)]


def test_reconnect_is_not_a_skip(tmp_path):
    d, mpd, p = make(tmp_path)
    mpd.consume = "0"
    mpd.add(LIB[0]["file"])
    mpd.play(0)
    d.on_event(p, {"player"})
    hist = d.hist_id
    d.song_id, d.playing = None, False  # what run_forever does when the connection drops
    d.on_event(p, {"player"})           # reconnected, same song still playing
    assert d.hist_id == hist
    rows = d.con.execute("SELECT skipped FROM history").fetchall()
    assert len(rows) == 1 and not rows[0]["skipped"]


def test_prefetches_next_song(tmp_path):
    d, mpd, p = make(tmp_path)
    mpd.consume = "0"
    for s in LIB[:3]:
        mpd.add(s["file"])
    mpd.play(0)
    d.on_event(p, {"player"})
    assert [s["file"] for s in d.prefetch.jobs] == [LIB[0]["file"], LIB[1]["file"]]
    d.on_event(p, {"playlist"})  # nothing changed: not queued again
    assert len(d.prefetch.jobs) == 2
