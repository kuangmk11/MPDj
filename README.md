# mpdj

MPD DJ: a rewrite of the old `/etc/myscripts/mpd` bash scripts as one Python tool with an
SQLite database. Put anything on and it keeps the queue going with similar music; one-key
macros for "more of this"; ratings, bans, lyrics, and a discovery report.

The original scripts are in [`legacy/`](legacy/), with a table of what replaced each one.

## Quick start

```bash
git clone git@github.com:kuangmk11/MPDj.git ~/src/mpdj && cd ~/src/mpdj
./install.sh --music-dir ~/Music --lastfm-key KEY --lastfm-user NAME
mpdj artist "joy division"        # play something; the daemon keeps the queue going
```

You need Ubuntu or Debian with systemd. Get a free Last.fm API key at
<https://www.last.fm/api/account/create>. Without one, the auto-queue falls back to the same
genre.

## Everyday use

```bash
mpdj status                 # what's playing, its rating, what's next
mpdj more similar           # swap the upcoming songs for similar artists
mpdj more album             # the rest of this album
mpdj rate 5                 # love it (also loves it on Last.fm after `mpdj lastfm-login`)
mpdj rate 1                 # never again: ban the song and skip
mpdj ban artist             # ban the whole artist and skip; `mpdj unban` undoes it
mpdj lyrics                 # lyrics for the current song
ncmpcpp                     # the same actions on Alt+key, see contrib/ncmpcpp/bindings
```

Check that the services are running with `systemctl --user status mpd mpdj`. Logs:
`journalctl --user -u mpdj -f`. Run `mpc update` after adding music.

## What's in this repo

| Path | What it is |
|---|---|
| `mpdj/` | the Python package (`cli.py` commands, `daemon.py`, `autoqueue.py`, `db.py`, …) |
| `install.sh` | sets up MPD, mpdj, ncmpcpp, scrobbling and the services on a new machine |
| `contrib/` | config files and systemd units that `install.sh` copies into place |
| `tests/` | `uv run pytest` (uses a fake MPD) |
| `legacy/` | the original 2014–2022 scripts, for reference only |

Files mpdj creates on your machine:

| Path | What it is |
|---|---|
| `~/.local/bin/mpdj` | the command (an editable install: `git pull` updates it) |
| `~/.config/mpdj/config.toml` | settings: Last.fm key, music folder, auto-queue numbers |
| `~/.local/share/mpdj/mpdj.db` | ratings, bans, play history, lyrics, Last.fm cache |
| `~/.config/systemd/user/mpdj.service` | runs `mpdj daemon` |
| `~/.config/mpd/` | MPD's config, database, queue state and playlists |

## Install on another machine

Ubuntu/Debian with systemd (on WSL: `[boot] systemd=true` in `/etc/wsl.conf`). Get this repo
onto the machine (`git clone`), then:

```bash
./install.sh --music-dir /mnt/mp3/MP3 --share //10.10.10.4/Music --mount /mnt/mp3 \
             --lastfm-key KEY --lastfm-user NAME
```

It installs mpd/mpc/ncmpcpp and mpdj, turns off Debian's system-wide MPD, writes the MPD, mpdj
and ncmpcpp configs (keeping any that exist), adds the ncmpcpp key bindings, and enables the
`mpd`, `mpdj`, `mpdscribble` (Last.fm scrobbling; asks for your Last.fm login and saves
the password as an MD5 hash) and, on WSL, audio-watchdog user services. `--no-scrobble` skips
scrobbling. `--share` mounts an SMB share
read-only and asks for its login, which goes in a root-only file. `./install.sh --help` lists
everything. It is safe to re-run.

To bring ratings, bans, play history and lyrics along: `mpdj backup mpdj.db` on the old
machine, copy the file over, and add `--db mpdj.db`.

## Manual setup (WSL)

```bash
sudo apt install mpd mpc ncmpcpp
cp contrib/mpd/mpd.conf ~/.config/mpd/mpd.conf     # set music_directory
mpd ~/.config/mpd/mpd.conf && mpc update

~/.local/bin/uv tool install -e ~/src/mpdj           # puts `mpdj` in ~/.local/bin
mpdj init                                            # writes ~/.config/mpdj/config.toml
mpdj lastfm-login                                    # optional: lets `rate 5` love on Last.fm
mpdj import-legacy --music-dir /path/to/mp3          # optional: old _lyrics, __similar, loved
```

Turn on consume mode (`mpc consume on`) and start the daemon:
`mpdj daemon`, or as a service:

```bash
cp contrib/systemd/mpdj.service ~/.config/systemd/user/
systemctl --user enable --now mpdj
```

If the music is on a network share, also copy `contrib/systemd/mpd.service.d/` to
`~/.config/systemd/user/`. Without it MPD can start before the share is mounted and fail every
file with "Too many levels of symbolic links".

**No sound after Windows sleep (WSL):** WSLg's PulseAudio hangs and MPD reports
`failed to connect: Timeout`. `contrib/wslg/wslg-audio-watchdog` checks it every minute and
restarts only that process (WSLg brings it back), then resumes MPD. Sound that turns
**choppy** after the screen wakes can't be detected (the server still answers): press Alt-F in
ncmpcpp or run `wslg-audio-watchdog --restart`. If it still stutters, press Alt-Shift-F or run
`wslg-audio-watchdog --full`: that also restarts weston, WSLg's compositor, which carries the
audio to Windows. It closes any open Linux GUI windows; terminals and MPD keep running.



```bash
cp contrib/wslg/wslg-audio-watchdog ~/.local/bin/
cp contrib/wslg/wslg-audio-watchdog.{service,timer} ~/.config/systemd/user/
systemctl --user enable --now wslg-audio-watchdog.timer
```

For ncmpcpp, append `contrib/ncmpcpp/bindings` to `~/.config/ncmpcpp/bindings` and merge
`contrib/ncmpcpp/config`.

## Commands

| Command | Old script | What it does |
|---|---|---|
| `mpdj more best [N]` | morebest, top10 | the artist's Last.fm top tracks that you have |
| `mpdj more similar [N]` | similar-artists-oneshot | a mix of similar artists |
| `mpdj more artist\|album\|genre\|song` | moreartist… | more of the same artist / rest of album / genre / other versions |
| `mpdj play artist\|album\|genre\|title NAME [-a] [-i] [-x] [-s]` | artist, album… | replace (or add/insert) the queue |
| `mpdj artist\|album\|genre\|title NAME [-a] [-i] [-x] [-s]` | artist, album… | shortcut for `play <tag>`; suggests close names when nothing matches |
| `mpdj queue [N] [--all]` (or `q`) | mpc-playlist | current and upcoming songs as a table |
| `mpdj again` / `next-album` / `prev-album` / `trim` / `shuffle` / `dedupe` | again, nextalbum… | queue helpers |
| `mpdj rate 1-5`, `mpdj love` | mpd_Nstar.sh | 5 = loved playlist + Last.fm love; 1 = ban song + skip |
| `mpdj ban artist\|album\|genre\|dir\|song\|string [VALUE] [--temp] [--purge]` | mpdskipper | ban and skip; `unban`, `bans` |
| `mpdj lyrics [--edit] [--delete] [--synced] [--search A T]` | lyrics.sh | lyrics from LRCLIB, stored in the DB |
| `mpdj bio`, `mpdj similar` | last-fm-bio | Last.fm artist info |
| `mpdj tabs [--bass] [--open]` | tab | Ultimate Guitar search link |
| `mpdj loved-sync` | lastfm-loved | builds the `lastfm-loved` playlist |
| `mpdj suggest [--fetch N] [--ignore NAME]` | suggestions | HTML report of artists you don't have |
| `mpdj backup FILE` | | copy the database (for moving machines) |
| `mpdj status` | mpc-status | what's playing, rating, queue, DB counts |
| `mpdj daemon` | similar-artists-new, mpdskipper, lyrics-fetcher-daemon | see below |

The `more` commands clear the upcoming queue first, like the old scripts; add `--keep` to append.

## The daemon

Waits on MPD events (no polling). When the song changes it logs play history (leaving within
30s counts as a skip), skips banned songs, and pre-fetches Last.fm info and lyrics. When consume
is on and fewer than 10 songs are left, it adds 10 more:

- similar artists you own, weighted by Last.fm's match score, with the current artist about 1 in 3;
- never the same artist twice in a row;
- no banned songs, nothing rated 1–2, nothing played in the last 14 days, nothing already queued;
- 4–5 star songs are 3× as likely;
- if Last.fm is unreachable it uses the cached list, then falls back to the same genre.

All of these numbers are in `~/.config/mpdj/config.toml`.

## Data

Everything lives in `~/.local/share/mpdj/mpdj.db`. Last.fm answers are cached for 7 days.
Ratings are also written as MPD `rating` stickers (0–10) so other clients can see them.

## Tests

```bash
uv run pytest
```
