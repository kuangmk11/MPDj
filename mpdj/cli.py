"""`mpdj` command line. Run `mpdj -h` or `mpdj <command> -h`."""
from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from . import autoqueue, config, db, legacy, lyrics, report, state
from .config import DATA_DIR
from .lastfm import LastFM, LastFMError
from .match import artist_songs, find_track
from .names import first, norm
from .player import Player

LOVED_PLAYLIST = "loved"
LASTFM_LOVED_PLAYLIST = "lastfm-loved"


class Ctx:
    """Lazily opened MPD connection, DB and Last.fm client."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._p = self._con = self._lfm = None

    @property
    def p(self) -> Player:
        if self._p is None:
            try:
                self._p = Player(self.cfg).connect()
            except OSError as e:
                die(f"can't reach MPD at {self.cfg.mpd_host}:{self.cfg.mpd_port} ({e})")
        return self._p

    @property
    def con(self):
        if self._con is None:
            self._con = db.connect(self.cfg.db_path)
        return self._con

    @property
    def lfm(self) -> LastFM:
        if self._lfm is None:
            self._lfm = LastFM(self.cfg, self.con)
        return self._lfm

    def current(self) -> dict:
        song = self.p.current()
        if not song:
            die("nothing playing")
        return song

    def close(self):
        if self._p:
            self._p.close()


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def label(song: dict) -> str:
    return f"{first(song.get('artist')) or '?'} - {first(song.get('title')) or song['file']}"


def show_added(songs: list[dict]) -> None:
    for s in songs:
        print(f"  + {label(s)}")
    print(f"added {len(songs)}")


# --- more <x> --------------------------------------------------------------
def _num(v, default: int) -> int:
    try:
        return int(str(first(v)).split("/")[0])
    except ValueError:
        return default


def _disc_track(s: dict) -> tuple[int, int, str]:
    return (_num(s.get("disc"), 1), _num(s.get("track"), 0), s["file"])


def cmd_more(ctx: Ctx, a) -> None:
    cur = ctx.current()
    p = ctx.p
    picker = autoqueue.Picker(p, ctx.con, ctx.lfm, ctx.cfg)
    if not a.keep:
        p.crop()
        picker.taken = {cur["file"]}
    n = a.n
    bans = picker.bans
    cur_key = (norm(first(cur.get("artist"))), norm(first(cur.get("title"))))

    def other(s):  # not the current song or another copy of it (e.g. in _loved)
        return (s["file"] != cur["file"] and s not in bans
                and (norm(first(s.get("artist"))), norm(first(s.get("title")))) != cur_key)

    if a.what == "best":
        songs = picker.top_tracks(cur, n)
        if not songs:
            print("no Last.fm top tracks found in the library")
    elif a.what == "similar":
        songs = picker.similar_mix(cur, n)
    elif a.what == "artist":
        songs = [s for s in artist_songs(p, first(cur.get("artist"))) if other(s)]
        random.shuffle(songs)
    elif a.what == "album":
        album = first(cur.get("album"))
        if not album:
            die("current song has no album tag")
        folder = cur["file"].rsplit("/", 1)[0]
        tracks = sorted((s for s in p.search("album", album, exact=True)
                         if s["file"].rsplit("/", 1)[0] == folder and s["file"] != cur["file"]),
                        key=_disc_track)
        # rest of the album after the current track, then the start of it
        after = [s for s in tracks if _disc_track(s) > _disc_track(cur)]
        songs = after + [s for s in tracks if s not in after]
    elif a.what == "genre":
        genre = first(cur.get("genre"))
        if not genre:
            die("current song has no genre tag")
        songs = [s for s in p.search("genre", genre, exact=True) if other(s)]
        random.shuffle(songs)
    elif a.what == "song":
        title = first(cur.get("title"))
        songs = [s for s in p.search("title", title)
                 if norm(first(s.get("title"))) == norm(title) and s["file"] != cur["file"]]
    else:
        die(f"unknown: {a.what}")

    if a.what in ("artist", "genre", "song") and a.n_given:
        songs = songs[:n]
    for s in songs:
        p.add(s["file"])
    show_added(songs)


# --- play <tag> <name> -----------------------------------------------------
def cmd_play(ctx: Ctx, a) -> None:
    name = " ".join(a.name)
    p = ctx.p
    songs = p.search(a.tag, name, exact=a.exact)
    if not songs:
        die(f"no {a.tag} matching '{name}'")
    songs.sort(key=lambda s: (first(s.get("artist")), first(s.get("album")), s["file"].rsplit("/", 1)[0], _disc_track(s), s["file"]))
    if a.insert:
        for s in reversed(songs):
            p.insert_next(s["file"])
    else:
        if not a.add:
            p.c.clear()
        for s in songs:
            p.add(s["file"])
        if not a.add:
            if a.shuffle:
                p.c.shuffle()
            p.play(0)
    p.ensure_playing()
    print(f"{'inserted' if a.insert else 'added'} {len(songs)} songs for {a.tag} '{name}'")


# --- queue helpers ---------------------------------------------------------
def cmd_again(ctx: Ctx, a) -> None:
    cur = ctx.current()
    ctx.p.insert_next(cur["file"])
    print(f"again: {label(cur)}")


def _album_blocks(q: list[dict]) -> list[tuple[int, int, str]]:
    """Runs of consecutive queue entries with the same album: [(start, end, album)]."""
    blocks = []
    for i, s in enumerate(q):
        alb = norm(first(s.get("album"))) + "|" + s["file"].rsplit("/", 1)[0]
        if blocks and blocks[-1][2] == alb:
            blocks[-1] = (blocks[-1][0], i, alb)
        else:
            blocks.append((i, i, alb))
    return blocks


def cmd_album_jump(ctx: Ctx, a) -> None:
    p = ctx.p
    st = p.status()
    if "song" not in st:
        die("nothing playing")
    pos = int(st["song"])
    blocks = _album_blocks(p.queue())
    idx = next(i for i, b in enumerate(blocks) if b[0] <= pos <= b[1])
    target = idx + (1 if a.cmd == "next-album" else -1)
    if not 0 <= target < len(blocks):
        die(f"no {'next' if a.cmd == 'next-album' else 'previous'} album")
    p.play(blocks[target][0])
    if a.cmd == "next-album" and a.trim:
        p.c.delete((0, blocks[target][0]))
    album = first(p.current().get("album"))
    print(f"playing: {label(p.current())}{f' [{album}]' if album else ''}")


def cmd_trim(ctx: Ctx, a) -> None:
    st = ctx.p.status()
    pos = int(st.get("song", 0))
    if pos > 0:
        ctx.p.c.delete((0, pos))
    print(f"removed {pos} played songs")


def cmd_shuffle(ctx: Ctx, a) -> None:
    st = ctx.p.status()
    start = int(st["song"]) + 1 if "song" in st else 0
    end = int(st.get("playlistlength", 0))
    if end - start > 1:
        ctx.p.c.shuffle((start, end))
    print(f"shuffled {max(end - start, 0)} upcoming songs")


def cmd_dedupe(ctx: Ctx, a) -> None:
    seen, drop = set(), []
    st = ctx.p.status()
    cur = int(st.get("song", -1))
    q = ctx.p.queue()
    # keep the playing copy, then the first copy of everything else
    if cur >= 0:
        seen.add(q[cur]["file"])
    for i, s in enumerate(q):
        if i == cur:
            continue
        if s["file"] in seen:
            drop.append(int(s["id"]))
        seen.add(s["file"])
    for sid in drop:
        ctx.p.c.deleteid(sid)
    print(f"removed {len(drop)} duplicates")


# --- ratings / bans --------------------------------------------------------
def cmd_rate(ctx: Ctx, a) -> None:
    cur = ctx.current()
    stars = a.stars
    state.set_rating(ctx.con, cur["file"], stars)
    ctx.p.set_sticker(cur["file"], "rating", str(stars * 2))  # 0-10 scale used by most MPD clients
    print(f"{'★' * stars}{'☆' * (5 - stars)}  {label(cur)}")
    if stars == 5:
        if cur["file"] not in ctx.p.playlist_files(LOVED_PLAYLIST):
            ctx.p.playlist_add(LOVED_PLAYLIST, cur["file"])
        if ctx.cfg.lastfm_api_secret:
            try:
                ctx.lfm.love(first(cur.get("artist")), first(cur.get("title")))
                print("loved on Last.fm")
            except (LastFMError, OSError) as e:
                print(f"Last.fm love failed: {e}", file=sys.stderr)
    elif stars == 1:
        state.add_ban(ctx.con, "song", cur["file"], temp=a.temp)
        ctx.p.next()
        print("banned and skipped")


def cmd_ban(ctx: Ctx, a) -> None:
    value = " ".join(a.value) if a.value else None
    song = None if value else ctx.current()
    v = state.ban_value(a.kind, song, value)
    if a.cmd == "unban":
        n = state.remove_ban(ctx.con, a.kind, v)
        if not n and not value:
            # the ban skipped past the song, so undo the newest ban of this kind instead
            row = ctx.con.execute("SELECT value FROM ban WHERE kind=? ORDER BY created_at DESC LIMIT 1",
                                  (a.kind,)).fetchone()
            if row:
                v = row["value"]
                n = state.remove_ban(ctx.con, a.kind, v)
        print(f"unbanned {a.kind} '{v}'" if n else f"no {a.kind} ban '{v}'")
        return
    state.add_ban(ctx.con, a.kind, v, temp=a.temp)
    print(f"banned {a.kind} '{v}'{' for 7 days' if a.temp else ''}")
    if song and not a.no_skip:
        ctx.p.next()
    if a.purge:
        bl = state.BanList(ctx.con)
        st = ctx.p.status()
        cur = int(st.get("song", -1))
        drop = [int(s["id"]) for i, s in enumerate(ctx.p.queue()) if i > cur and s in bl]
        for sid in drop:
            ctx.p.c.deleteid(sid)
        print(f"removed {len(drop)} banned songs from the queue")


def cmd_bans(ctx: Ctx, a) -> None:
    rows = state.active_bans(ctx.con)
    if not rows:
        print("no bans")
    for r in rows:
        exp = f"  (until {time.strftime('%Y-%m-%d', time.localtime(r['expires_at']))})" if r["expires_at"] else ""
        print(f"{r['kind']:7} {r['value']}{exp}")


# --- info ------------------------------------------------------------------
def _artist_arg(ctx: Ctx, a) -> str:
    return " ".join(a.artist) if a.artist else first(ctx.current().get("artist"))


def cmd_bio(ctx: Ctx, a) -> None:
    info = ctx.lfm.info(_artist_arg(ctx, a), refresh=a.refresh)
    if not info:
        die("no info (check Last.fm api_key)")
    print(f"{info['name']}\n{info['tags'] or ''}\n\n{info['bio'] or '(no bio)'}\n\n{info['url'] or ''}")


def cmd_similar(ctx: Ctx, a) -> None:
    artist = _artist_arg(ctx, a)
    have = {norm(x) for x in ctx.p.list_artists()}
    for name, match in ctx.lfm.similar(artist, refresh=a.refresh)[: a.n]:
        print(f"{'●' if norm(name) in have else ' '} {match:4.2f}  {name}")
    print("● = in your library")


def cmd_lyrics(ctx: Ctx, a) -> None:
    if a.search:
        song = {"artist": a.search[0], "title": a.search[1], "file": ""}
    else:
        song = ctx.current()
    artist, title = first(song.get("artist")), first(song.get("title"))
    if a.delete:
        n = lyrics.delete(ctx.con, artist, title)
        p = lyrics.ncmpcpp_path(ctx.cfg.ncmpcpp_lyrics_dir, artist, title) if ctx.cfg.ncmpcpp_lyrics_dir else None
        if p and p.exists():
            p.unlink()
        print("deleted" if n else "no lyrics stored")
        return
    row = lyrics.lookup(ctx.con, song, refresh=a.refresh)
    text = lyrics.text_of(row)
    if a.edit:
        editor = os.environ.get("EDITOR", "nano")
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
            f.write(text or "")
            tmp = f.name
        subprocess.call([editor, tmp])
        new = Path(tmp).read_text().strip()
        os.unlink(tmp)
        if new and new != (text or "").strip():
            lyrics.save(ctx.con, artist, title, new, row["synced"] if row else None, "manual")
            p = lyrics.ncmpcpp_path(ctx.cfg.ncmpcpp_lyrics_dir, artist, title) if ctx.cfg.ncmpcpp_lyrics_dir else None
            if p and p.exists():
                p.write_text(new + "\n")
            print("saved")
        return
    if not text:
        die(f"no lyrics found for {artist} - {title}")
    if a.synced and row["synced"]:
        print(row["synced"])
    else:
        print(f"{artist} - {title}\n\n{text}")
    if song.get("file"):
        lyrics.export_ncmpcpp(ctx.cfg.ncmpcpp_lyrics_dir, song, text)


def cmd_tabs(ctx: Ctx, a) -> None:
    cur = ctx.current()
    q = f"{first(cur.get('artist'))} {first(cur.get('title'))}"
    url = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + quote_plus(q)
    if a.bass:
        url = "https://www.ultimate-guitar.com/search.php?search_type=title&type=400&value=" + quote_plus(q)
    print(url)
    if a.open:
        for opener in (["wslview", url], ["explorer.exe", url]):
            try:
                subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except FileNotFoundError:
                continue
        webbrowser.open(url)


def cmd_status(ctx: Ctx, a) -> None:
    st = ctx.p.status()
    cur = ctx.p.current()
    if cur:
        stars = ctx.con.execute("SELECT stars FROM rating WHERE file=?", (cur["file"],)).fetchone()
        album = first(cur.get("album"))
        print(f"{st.get('state')}: {label(cur)}{f'  [{album}]' if album else ''}"
              f"{'  ' + '★' * stars['stars'] if stars else ''}")
        reason = state.BanList(ctx.con).reason(cur)
        if reason:
            print(f"  (banned by {reason})")
    else:
        print(st.get("state", "?"))
    print(f"queue: {ctx.p.songs_after_current()} upcoming   consume: {'on' if st.get('consume') == '1' else 'off'}"
          f"   random: {'on' if st.get('random') == '1' else 'off'}")
    c = ctx.con
    counts = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("history", "rating", "ban", "lyrics", "similar", "artist")}
    print("db: " + "  ".join(f"{k} {v}" for k, v in counts.items()))


# --- Last.fm ---------------------------------------------------------------
def cmd_lastfm_login(ctx: Ctx, a) -> None:
    import getpass
    user = a.user or ctx.cfg.lastfm_username or input("Last.fm username: ")
    pw = getpass.getpass("Last.fm password (sent once to Last.fm, not stored): ")
    try:
        ctx.lfm.login(user, pw)
    except (LastFMError, OSError) as e:
        die(f"login failed: {e}")
    print("logged in; session saved in the mpdj database")


def cmd_loved_sync(ctx: Ctx, a) -> None:
    user = a.user or ctx.cfg.lastfm_username
    if not user:
        die("set [lastfm] username in the config or pass --user")
    loved = ctx.lfm.loved_tracks(user)
    print(f"{len(loved)} loved tracks on Last.fm")
    ratings = state.ratings(ctx.con)
    by_artist: dict[str, list[dict]] = {}
    found, missing = [], []
    for artist, title in loved:
        if artist not in by_artist:
            by_artist[artist] = artist_songs(ctx.p, artist)
        s = find_track(by_artist[artist], title, ratings=ratings)
        (found if s else missing).append(s or (artist, title))
    ctx.p.playlist_clear(LASTFM_LOVED_PLAYLIST)
    for s in found:
        ctx.p.playlist_add(LASTFM_LOVED_PLAYLIST, s["file"])
        if s["file"] not in ratings:
            state.set_rating(ctx.con, s["file"], 5)
    miss_file = DATA_DIR / "loved-missing.txt"
    miss_file.parent.mkdir(parents=True, exist_ok=True)
    miss_file.write_text("".join(f"{ar} - {t}\n" for ar, t in missing))
    print(f"playlist '{LASTFM_LOVED_PLAYLIST}': {len(found)} songs; "
          f"{len(missing)} not in library (list in {miss_file})")


def cmd_suggest(ctx: Ctx, a) -> None:
    if a.ignore:
        name = " ".join(a.ignore)
        ctx.con.execute("INSERT OR IGNORE INTO suggest_ignore(norm,name) VALUES(?,?)", (norm(name), name))
        print(f"won't suggest '{name}' again")
        return
    artists = ctx.p.list_artists()
    if a.fetch:
        todo = [x for x in artists if x and not ctx.con.execute(
            "SELECT 1 FROM fetch_log WHERE kind='similar' AND key=?", (norm(x),)).fetchone()]
        todo = todo[: a.fetch]
        for i, x in enumerate(todo, 1):
            print(f"\r fetching similar artists {i}/{len(todo)} ", end="", flush=True)
            ctx.lfm.similar(x)
            time.sleep(0.25)  # stay well under Last.fm's rate limit
        print()
    seeds = ctx.con.execute("SELECT COUNT(DISTINCT artist) FROM similar").fetchone()[0]
    rows = report.suggestions(ctx.con, artists, a.min)
    out = report.write_html(Path(a.out).expanduser(), rows[: a.limit], ctx.cfg.suggest_links, seeds)
    for n, name, _ in rows[:20]:
        print(f"{n:4}  {name}")
    print(f"{len(rows)} suggestions from {seeds} artists' similar lists -> {out}")
    if seeds < 50:
        print("tip: `mpdj suggest --fetch 500` fills in similar lists for more of your library first")


def cmd_import_legacy(ctx: Ctx, a) -> None:
    music = Path(a.music_dir or ctx.cfg.music_dir).expanduser()
    if not music.is_dir():
        die(f"music dir not found: {music}")
    # Old layout kept everything inside the music folder; newer one has
    # <root>/__metadata and <root>/_PLAYLISTS next to it.
    meta = Path(a.meta_dir).expanduser() if a.meta_dir else (
        music.parent / "__metadata" if (music.parent / "__metadata").is_dir() else music)
    playlists = Path(a.playlist_dir).expanduser() if a.playlist_dir else (
        music.parent / "_PLAYLISTS" if (music.parent / "_PLAYLISTS").is_dir() else music / "_PLAYLISTS")
    c = ctx.con
    print(f"importing (read-only) from music={music} metadata={meta} playlists={playlists}")
    print(f"  lyrics:        {legacy.import_lyrics(c, meta)}")
    print(f"  similar lists: {legacy.import_similar(c, meta)}")
    print(f"  suggest ignore:{legacy.import_blacklist(c, meta)}")
    print(f"  loved -> 5★:   {legacy.import_loved(c, music, playlists)}")
    if a.tags:
        print("  reading MYRATING tags from every mp3 (slow)...")
        print(f"  tag ratings:   {legacy.import_rating_tags(c, music)}")


def cmd_init(ctx: Ctx, a) -> None:
    if config.write_example():
        print(f"wrote {config.CONFIG_FILE} — fill in [lastfm] api_key and [mpd] music_dir")
    else:
        print(f"{config.CONFIG_FILE} already exists")


def cmd_daemon(ctx: Ctx, a) -> None:
    from . import daemon
    daemon.main(ctx.cfg)


# --- argument parsing ------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mpdj", description="MPD DJ: smart queueing, ratings, bans, lyrics.")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

    def add(name, fn, help, **kw):
        sp = sub.add_parser(name, help=help, **kw)
        sp.set_defaults(fn=fn)
        return sp

    sp = add("more", cmd_more, "queue more like the current song (clears upcoming first)")
    sp.add_argument("what", choices=["best", "similar", "artist", "album", "genre", "song"])
    sp.add_argument("n", nargs="?", type=int, help="how many (default 10 for best/similar, all otherwise)")
    sp.add_argument("--keep", action="store_true", help="keep the upcoming queue instead of clearing it")

    sp = add("play", cmd_play, "replace the queue with an artist/album/genre/title")
    sp.add_argument("tag", choices=["artist", "album", "genre", "title", "any"])
    sp.add_argument("name", nargs="+")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("-a", "--add", action="store_true", help="append instead of replacing")
    g.add_argument("-i", "--insert", action="store_true", help="insert after the current song")
    sp.add_argument("-x", "--exact", action="store_true", help="exact tag match")
    sp.add_argument("-s", "--shuffle", action="store_true")

    add("again", cmd_again, "play the current song again next")
    sp = add("next-album", cmd_album_jump, "jump to the next album in the queue")
    sp.add_argument("--trim", action="store_true", help="also remove everything before it")
    add("prev-album", cmd_album_jump, "jump to the previous album in the queue").set_defaults(trim=False)
    add("trim", cmd_trim, "remove already-played songs from the queue")
    add("shuffle", cmd_shuffle, "shuffle the upcoming songs, keep the current one playing")
    add("dedupe", cmd_dedupe, "remove duplicate songs from the queue")

    sp = add("rate", cmd_rate, "rate the current song 1-5 (5 = love, 1 = ban + skip)")
    sp.add_argument("stars", type=int, choices=range(1, 6))
    sp.add_argument("--temp", action="store_true", help="with 1: ban for 7 days only")
    add("love", cmd_rate, "same as `rate 5`").set_defaults(stars=5, temp=False)

    for name, help in (("ban", "ban the current song's artist/album/... and skip"), ("unban", "remove a ban")):
        sp = add(name, cmd_ban, help)
        sp.add_argument("kind", choices=state.BAN_KINDS)
        sp.add_argument("value", nargs="*", help="default: from the current song")
        sp.add_argument("--temp", action="store_true", help="ban for 7 days only")
        sp.add_argument("--no-skip", action="store_true", help="don't skip the current song")
        sp.add_argument("--purge", action="store_true", help="also remove banned songs from the queue")
    add("bans", cmd_bans, "list bans")

    sp = add("bio", cmd_bio, "Last.fm artist bio")
    sp.add_argument("artist", nargs="*")
    sp.add_argument("--refresh", action="store_true")
    sp = add("similar", cmd_similar, "list similar artists")
    sp.add_argument("artist", nargs="*")
    sp.add_argument("-n", type=int, default=30)
    sp.add_argument("--refresh", action="store_true")

    sp = add("lyrics", cmd_lyrics, "lyrics for the current song")
    sp.add_argument("--edit", action="store_true")
    sp.add_argument("--delete", action="store_true")
    sp.add_argument("--refresh", action="store_true", help="fetch again even if stored")
    sp.add_argument("--synced", action="store_true", help="print time-synced LRC if available")
    sp.add_argument("--search", nargs=2, metavar=("ARTIST", "TITLE"))

    sp = add("tabs", cmd_tabs, "Ultimate Guitar search link for the current song")
    sp.add_argument("--bass", action="store_true")
    sp.add_argument("--open", action="store_true", help="open in the browser")

    add("status", cmd_status, "what's playing, rating, queue, DB counts")

    sp = add("lastfm-login", cmd_lastfm_login, "log in to Last.fm (needed for love)")
    sp.add_argument("--user")
    sp = add("loved-sync", cmd_loved_sync, f"build the '{LASTFM_LOVED_PLAYLIST}' playlist from Last.fm loved tracks")
    sp.add_argument("--user")

    sp = add("suggest", cmd_suggest, "HTML report of artists you might want")
    sp.add_argument("--fetch", type=int, default=0, metavar="N", help="first fetch similar lists for up to N library artists")
    sp.add_argument("--min", type=int, default=3, help="minimum times seen")
    sp.add_argument("--limit", type=int, default=500)
    sp.add_argument("--out", default=str(DATA_DIR / "suggestions.html"))
    sp.add_argument("--ignore", nargs="+", metavar="ARTIST", help="never suggest this artist")

    sp = add("import-legacy", cmd_import_legacy, "import old _lyrics/__similar/loved data")
    sp.add_argument("--music-dir")
    sp.add_argument("--meta-dir", help="folder holding _lyrics, __similar, __suggestions")
    sp.add_argument("--playlist-dir", help="folder holding linux/loved-master.lin.m3u")
    sp.add_argument("--tags", action="store_true", help="also read MYRATING tags from every mp3 (slow)")

    add("init", cmd_init, "write a starter config file")
    add("daemon", cmd_daemon, "watch MPD: history, ban skipping, auto-queue, prefetch")
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.cmd == "more":
        args.n_given = args.n is not None
        if args.n is None:
            args.n = 10
    ctx = Ctx(config.load())
    try:
        args.fn(ctx, args)
    except KeyboardInterrupt:
        pass
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
