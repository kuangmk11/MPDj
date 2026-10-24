import random
from collections import Counter

import pytest

from mpdj import cli, db, lyrics, state
from mpdj.autoqueue import Picker, needs_refill
from mpdj.config import Config
from mpdj.match import find_track
from mpdj.names import is_live, norm, norm_artist, norm_title
from mpdj.player import Player

from .fakes import FakeLastFM, FakeMPD, song

LIB = (
    [song("Joy Division", t, "Unknown Pleasures", i) for i, t in enumerate(
        ["Disorder", "Day of the Lords", "Candidate", "Insight", "New Dawn Fades", "She's Lost Control",
         "Shadowplay", "Wilderness", "Interzone", "I Remember Nothing"], 1)]
    + [song("Joy Division", "Love Will Tear Us Apart", "Substance", 1),
       song("Joy Division", "Love Will Tear Us Apart [Live]", "Still", 3)]
    + [song("New Order", f"NO {i}", "Movement", i) for i in range(1, 9)]
    + [song("The Cure", f"Cure {i}", "Pornography", i) for i in range(1, 9)]
    + [song("Bauhaus", f"Bauhaus {i}", "In the Flat Field", i) for i in range(1, 9)]
    + [song("Siouxsie and the Banshees", f"Sioux {i}", "Juju", i) for i in range(1, 9)]
    + [song("Abba", f"Abba {i}", "Gold", i, genre="Pop") for i in range(1, 5)]
)
SIMILAR = {"joy division": [("New Order", 1.0), ("The Cure", 0.6), ("Bauhaus", 0.5),
                            ("Siouxsie & The Banshees", 0.4), ("Not In Library", 0.9)]}
TOP = {"joy division": ["Love Will Tear Us Apart", "Disorder", "She's Lost Control", "Atmosphere"]}


@pytest.fixture
def env():
    cfg = Config()
    con = db.connect(":memory:")
    mpd = FakeMPD(LIB)
    p = Player(cfg, client=mpd)
    mpd.add(LIB[0]["file"])  # Joy Division - Disorder
    mpd.play(0)
    return cfg, con, mpd, p


# --- names ---------------------------------------------------------------
def test_norm_matches_old_sed_rules():
    assert norm("Siouxsie & The Banshees") == norm("siouxsie and the banshees")
    assert norm("She's Lost Control") == "shes lost control"
    assert norm("Zero Le Crêche") == "zero le creche"
    assert norm_title("Atmosphere (2007 Remaster)") == "atmosphere"
    assert norm_title("Ceremony [Live]") == "ceremony"
    assert norm_title("Disorder - 2007 Remaster") == "disorder"
    assert norm_title("Love Will Tear Us Apart - Pennine Version") == "love will tear us apart"
    assert norm_title("Mr. Self-Destruct") == "mr self destruct"


def test_aliases():
    al = {"warsaw": "joy division", "christian death*": "christian death"}
    assert norm_artist("Warsaw", al) == "joy division"
    assert norm_artist("Christian Death feat. Rozz Williams", al) == "christian death"
    assert norm_artist("New Order", al) == "new order"


def test_is_live():
    assert is_live("Ceremony [Live]")
    assert is_live("Transmission (Live at Les Bains Douches)")
    assert not is_live("Living in the Ice Age")


# --- matching --------------------------------------------------------------
def test_find_track_prefers_studio_and_skips_avoided():
    jd = [s for s in LIB if s["artist"] == "Joy Division"]
    hit = find_track(jd, "Love Will Tear Us Apart")
    assert hit["album"] == "Substance"
    assert find_track(jd, "shes lost control")["title"] == "She's Lost Control"
    assert find_track(jd, "Atmosphere") is None
    assert find_track(jd, "Disorder", avoid={LIB[0]["file"]}) is None


# --- auto-queue ------------------------------------------------------------
def test_similar_mix_rules(env):
    cfg, con, mpd, p = env
    random.seed(1)
    picker = Picker(p, con, FakeLastFM(SIMILAR), cfg, rng=random.Random(1))
    picks = picker.similar_mix(p.current(), 10)
    assert len(picks) == 10
    artists = [s["artist"] for s in picks]
    assert "Abba" not in artists                       # not similar
    assert all(a != b for a, b in zip(["Joy Division"] + artists, artists))  # no repeats in a row
    assert "Joy Division" in artists                    # seed artist mixed in
    assert len({s["file"] for s in picks}) == 10        # no duplicates
    assert LIB[0]["file"] not in {s["file"] for s in picks}  # not the playing song
    assert "Siouxsie and the Banshees" in dict(picker.similar_pool("Joy Division"))


def test_similar_mix_respects_bans_ratings_history(env):
    cfg, con, mpd, p = env
    state.add_ban(con, "artist", "new order")
    cure1 = next(s for s in LIB if s["title"] == "Cure 1")
    state.set_rating(con, cure1["file"], 1)
    bauhaus1 = next(s for s in LIB if s["title"] == "Bauhaus 1")
    state.start_play(con, bauhaus1)
    picker = Picker(p, con, FakeLastFM(SIMILAR), cfg, rng=random.Random(2))
    files = {s["file"] for s in picker.similar_mix(p.current(), 30)}
    assert not any("New Order" in f for f in files)
    assert cure1["file"] not in files
    assert bauhaus1["file"] not in files


def test_similar_mix_falls_back_to_genre(env):
    cfg, con, mpd, p = env
    picker = Picker(p, con, FakeLastFM({}), cfg, rng=random.Random(3))
    picks = picker.similar_mix(p.current(), 5)
    assert len(picks) == 5
    assert all(s["genre"] == "Darkwave" for s in picks)


def test_top_tracks(env):
    cfg, con, mpd, p = env
    picker = Picker(p, con, FakeLastFM(top=TOP), cfg)
    titles = [s["title"] for s in picker.top_tracks(p.current(), 10)]
    # skips the playing song (Disorder) and missing ones; studio version wins
    assert titles == ["Love Will Tear Us Apart", "She's Lost Control"]


def test_needs_refill(env):
    cfg, con, mpd, p = env
    assert needs_refill(p, cfg)
    mpd.consume = "0"
    assert not needs_refill(p, cfg)
    cfg.require_consume = False
    for s in LIB[1:12]:
        mpd.add(s["file"])
    assert not needs_refill(p, cfg)


# --- bans / history ----------------------------------------------------------
def test_ban_kinds_and_expiry(env):
    cfg, con, mpd, p = env
    cur = p.current()
    state.add_ban(con, "dir", state.ban_value("dir", cur))
    assert state.BanList(con).reason(cur) == "dir"
    state.remove_ban(con, "dir", state.ban_value("dir", cur))
    state.add_ban(con, "string", state.ban_value("string", value="DISORDER"))
    assert state.BanList(con).reason(cur) == "string"
    con.execute("UPDATE ban SET expires_at=1")  # expired long ago
    assert state.BanList(con).reason(cur) is None


def test_skip_detection():
    con = db.connect(":memory:")
    h = state.start_play(con, LIB[0])
    assert state.end_play(con, h, 5, 30, 200) is True
    h = state.start_play(con, LIB[0])
    assert state.end_play(con, h, 199, 30, 200) is False
    h = state.start_play(con, LIB[0])
    assert state.end_play(con, h, 15, 30, 16) is False  # short song that finished


def test_cache_freshness():
    con = db.connect(":memory:")
    assert not db.is_fresh(con, "similar", "x", 3600 * 24)
    db.mark_fetched(con, "similar", "x", True)
    assert db.is_fresh(con, "similar", "x", 3600 * 24)
    con.execute("UPDATE fetch_log SET fetched_at = fetched_at - 7200")
    db.mark_fetched(con, "similar", "y", False)
    con.execute("UPDATE fetch_log SET fetched_at = fetched_at - 7200 WHERE key='y'")
    assert db.is_fresh(con, "similar", "x", 3600 * 24)   # ok rows last the TTL
    assert not db.is_fresh(con, "similar", "y", 3600 * 24)  # failures retry after an hour


# --- lyrics -----------------------------------------------------------------
def test_lyrics_store_and_strip():
    con = db.connect(":memory:")
    lyrics.save(con, "Joy Division", "Disorder (Remaster)", None, "[00:01.00] I've been waiting\n[00:05.20] for a guide", "t")
    row = lyrics.get_cached(con, "joy division", "Disorder")
    assert lyrics.text_of(row) == "I've been waiting\nfor a guide"
    assert lyrics.ncmpcpp_path("/tmp/x", "AC/DC", "What?").name == "ACDC - What.txt"


# --- CLI macros ---------------------------------------------------------------
class _Ctx(cli.Ctx):
    def __init__(self, cfg, con, p, lfm):
        super().__init__(cfg)
        self._p, self._con, self._lfm = p, con, lfm

    def close(self):
        pass


def run(ctx, *argv):
    args = cli.build_parser().parse_args(argv)
    if args.cmd == "more":
        args.n_given = args.n is not None
        args.n = args.n or 10
    args.fn(ctx, args)


def test_more_album_orders_rest_then_start(env):
    cfg, con, mpd, p = env
    mpd.q.clear()
    mpd.add(LIB[3]["file"])  # track 4 of Unknown Pleasures
    for s in LIB[20:23]:
        mpd.add(s["file"])  # junk that crop should remove
    mpd.play(0)
    run(_Ctx(cfg, con, p, FakeLastFM()), "more", "album")
    tracks = [int(s["track"]) for s in mpd.q]
    assert tracks == [4, 5, 6, 7, 8, 9, 10, 1, 2, 3]


def test_more_best_and_again(env):
    cfg, con, mpd, p = env
    ctx = _Ctx(cfg, con, p, FakeLastFM(top=TOP))
    run(ctx, "more", "best")
    assert [s["title"] for s in mpd.q] == ["Disorder", "Love Will Tear Us Apart", "She's Lost Control"]
    run(ctx, "again")
    assert mpd.q[1]["title"] == "Disorder"


def test_next_prev_album_and_dedupe(env):
    cfg, con, mpd, p = env
    ctx = _Ctx(cfg, con, p, FakeLastFM())
    for s in LIB[1:3] + LIB[12:14] + LIB[1:2]:
        mpd.add(s["file"])
    run(ctx, "dedupe")
    assert len(mpd.q) == 5
    run(ctx, "next-album")
    assert mpd.q[mpd.pos]["artist"] == "New Order"
    run(ctx, "prev-album")
    assert mpd.pos == 0


def test_rate_5_and_1(env):
    cfg, con, mpd, p = env
    lfm = FakeLastFM()
    ctx = _Ctx(cfg, con, p, lfm)
    mpd.add(LIB[1]["file"])
    run(ctx, "rate", "5")
    assert state.ratings(con)[LIB[0]["file"]] == 5
    assert mpd.playlists["loved"] == [LIB[0]["file"]]
    assert mpd.stickers[(LIB[0]["file"], "rating")] == "10"
    run(ctx, "rate", "1")
    assert state.ratings(con)[LIB[0]["file"]] == 1
    assert mpd.q[mpd.pos]["file"] == LIB[1]["file"]  # skipped
    assert state.BanList(con).reason(LIB[0]) == "song"


def test_play_replace_add_insert(env):
    cfg, con, mpd, p = env
    ctx = _Ctx(cfg, con, p, FakeLastFM())
    run(ctx, "play", "artist", "bauhaus")
    assert Counter(s["artist"] for s in mpd.q) == {"Bauhaus": 8}
    run(ctx, "play", "album", "Gold", "--insert")
    assert mpd.q[1]["artist"] == "Abba" and len(mpd.q) == 12


class FakeHTTP:
    """requests.Session stand-in: answers by URL substring, in order."""
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        for key, answers in self.routes.items():
            if key in url:
                code, body = answers.pop(0) if len(answers) > 1 else answers[0]
                return FakeResponse(code, body)
        return FakeResponse(404, {})


class FakeResponse:
    def __init__(self, code, body):
        self.status_code, self._body = code, body

    def json(self):
        return self._body


def test_lyrics_clean_title_and_fuzzy_match(monkeypatch):
    monkeypatch.setattr(lyrics.time, "sleep", lambda s: None)
    assert lyrics.clean_title("Kameradschaft [Live]") == "Kameradschaft"
    hit = {"artistName": "Forseti", "trackName": "Gesang der Jünglinge", "plainLyrics": "Heilig"}
    http = FakeHTTP({"/get": [(404, {})], "/search": [(503, {}), (200, [hit])]})
    got = lyrics.fetch_lrclib("Forseti", "Gesang Der Junglinge [Live]", http=http)
    assert got["plainLyrics"] == "Heilig"
    assert http.calls[0][1]["track_name"] == "Gesang Der Junglinge"  # brackets dropped


def test_lyrics_busy_is_not_cached_as_miss(monkeypatch):
    monkeypatch.setattr(lyrics.time, "sleep", lambda s: None)
    monkeypatch.setattr(lyrics, "fetch_lrclib", lambda *a, **k: (_ for _ in ()).throw(lyrics.Busy("503")))
    monkeypatch.setattr(lyrics, "fetch_lyrics_ovh", lambda a, t: "from ovh")
    con = db.connect(":memory:")
    row = lyrics.lookup(con, {"artist": "A", "title": "T"})
    assert lyrics.text_of(row) == "from ovh" and row["source"] == "lyrics.ovh"
    monkeypatch.setattr(lyrics, "fetch_lyrics_ovh", lambda a, t: None)
    assert lyrics.lookup(con, {"artist": "B", "title": "T"}) is None
    assert not db.is_fresh(con, "lyrics", "b|t", 3600)  # will be retried next time


def test_strip_brackets():
    from mpdj.names import strip_brackets
    assert strip_brackets("Song (Live) [2011 Remaster]") == "Song"
    assert strip_brackets("Song [Live (Demo)]") == "Song"
    assert strip_brackets("Song (Live") == "Song"
    assert lyrics.clean_title("[Untitled]") == "[Untitled]"


def test_did_you_mean(monkeypatch):
    from mpdj.cli import _did_you_mean
    from mpdj.config import Config
    from mpdj.player import Player
    from .fakes import FakeMPD
    lib = [{"file": "a.mp3", "artist": "Vàli", "title": "x"}, {"file": "b.mp3", "artist": "Forseti", "title": "y"},
           {"file": "c.mp3", "artist": "Cavaliers", "title": "z"}]
    p = Player(Config(), client=FakeMPD(lib))
    assert _did_you_mean(p, "artist", "vali") == ["Vàli"]        # accents only
    assert _did_you_mean(p, "artist", "forsetti") == ["Forseti"]  # one close typo
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert _did_you_mean(p, "artist", "zzzz") == []
