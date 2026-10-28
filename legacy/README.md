# The original scripts (reference only)

These are the bash, Python, Ruby and PHP scripts that mpdj replaces, written 2014–2022 for a
home server called `gargoyle2`, where they lived in `/etc/myscripts/mpd`. They're kept here so
you can see where each mpdj feature came from and how the old version did it.

**Don't run them.** They're stored non-executable on purpose. They expect a 2015-era system:
music at `/storage/dd1/mp3`, `/etc/myscripts/colors.sh`, `~/.mpdskip/config`, `eyeD3`,
`xml_grep`, `beep`, sound cards named `Front` and `Surround`, and lyrics sites that no longer
exist. Many also run as root.

## What changed before they were added here

- **Secrets removed.** Last.fm API keys, an API secret, two Last.fm password hashes and three
  email addresses were replaced with `REDACTED_…` placeholders. Nothing else in the code was
  edited.
- **Left out:** `last_to_libre/exported_tracks.txt` (a 40 MB export of the full Last.fm play
  history), compiled `.pyc` files, the `lastfmpdqc.tar.gz` source archive (its files are
  already here unpacked), `mpdcron/mpdcron.pid` and a stray guitar tab (`mpdcron/.txt`).
- File dates are lost in git. The originals, with their dates, are in the backup at
  `\\TRUENAS\Backups-RW\gargoyle2\etc\myscripts\mpd`.

`lyrics/variables` was the shared settings file that most scripts loaded with `source`. It
held the Last.fm key and the Last.fm query URLs. mpdj keeps these settings in
`~/.config/mpdj/config.toml`.

## Old script → mpdj

### Building the queue

| Old | What it did | Now |
|---|---|---|
| `artist`, `album`, `genre`, `title` (`_backup/` has 2015 versions) | search the library, clear the queue and play; `-a` adds instead | `mpdj artist\|album\|genre\|title NAME` (same `-a`, plus `-i`, `-x`, `-s`) |
| `moreartist`, `morealbum`, `moregenre`, `moresong` | more of the current artist / rest of album / genre / other versions | `mpdj more artist\|album\|genre\|song` |
| `morebest`, `top10` | the artist's Last.fm top tracks that are in the library | `mpdj more best` |
| `similar-artists-oneshot` | queue a batch of similar artists once | `mpdj more similar` |
| `similar-artists-new`, `lfm-plex` (a 2022 copy), `mpd-fetcher` | refill the queue with similar artists when it ran low | the `mpdj daemon` auto-queue |
| `again` | play the current song again next | `mpdj again` |
| `nextalbum`, `prevalbum` | jump to the next or previous album in the queue | `mpdj next-album`, `mpdj prev-album` |
| `mpd-trim-played` | remove songs already played | `mpdj trim` (or consume mode) |
| `shuffle` | shuffle the queue through a saved playlist | `mpdj shuffle` |
| `remove_duplicates` | drop repeated songs from the queue | `mpdj dedupe` |
| `mpc-playlist`, `mpc-status`, `mpc-path`, `php/*`, `lyrics/growl.bash` | show the queue / current song / file path (the `php/` ones fed a web page) | `mpdj queue`, `mpdj status` |
| `lyrics/playlist-edit` | pick songs to remove from a menu | dropped: use ncmpcpp |
| `albumbler`, `albumbler.py` (Kyle Keen, GPLv2) | play a random album, weighted by what you skip | dropped: the auto-queue covers it |

### Ratings, loved tracks and bans

| Old | What it did | Now |
|---|---|---|
| `mpd_1star.sh` … `mpd_5star.sh` | write a `MYRATING` ID3 tag (1 also bans and skips, 5 also loves on Last.fm) | `mpdj rate 1-5`, `mpdj love`. Ratings go in the database and MPD stickers; files aren't touched |
| `lastfm-mpd-cli.py` (Kyle Racette, GPLv3) | love the current song on Last.fm | `mpdj lastfm-login` once, then `mpdj rate 5` |
| `myrating-to-sticker-db` | copy `MYRATING` tags into MPD stickers | `mpdj import-legacy --tags` |
| `lastfm-loved`, `lastfm-loved-playlist`, `loved-playlist-gen`, `fav-sync` | build `loved-master.lin.m3u` from Last.fm loved tracks and 5-star songs | `mpdj loved-sync` (`lastfm-loved` playlist) |
| `mpdskipper`, `mpdskipper.bak` | skip blacklisted artists, albums, genres, folders and words; temporary bans | `mpdj ban … [--temp]`, `unban`, `bans`, and the daemon skips them |
| `mpd_acoustic.sh`, `mpd_bass.sh`, `mpd_game.sh`, `mpd_guitar.sh`, `mpd_mark.sh` | tag the song with a custom ID3 flag | dropped |

### Lyrics, artist info and tabs (`lyrics/`)

| Old | What it did | Now |
|---|---|---|
| `lyrics.sh`, `lyrics-fetcher.sh`, `lyrics-fetcher-whole-system`, `lyrics-fetcher-daemon`, `quietlyrics`, `ncmpc-lyrics`, `../autolyrics.sh` | fetch and show lyrics, save them in `_lyrics/` | `mpdj lyrics` (LRCLIB, then lyrics.ovh; the daemon pre-fetches) |
| `lyric-search`, `az-lyrics`, `darklyrics`, `metro-lyrics`, `song-lyrics`, `song-meanings`, `songtexte` | search one site each | dropped: those sites block scripts or are gone. `mpdj lyrics --search A T`, `--edit` for anything missing |
| `_old/`, `orig/`, `.support/` | earlier versions, LyricWiki and Leo's Lyrics fetchers (both sites closed) | — |
| `translyrics` | translate lyrics with `trans` | dropped |
| `last-fm-bio`, `last-fm-bio-manual`, `last-fm-bio-manual-single`, `VA-lastfm-artist-check` | Last.fm bio and similar artists, cached as XML | `mpdj bio`, `mpdj similar` (cached 7 days in the database) |
| `ultimate-guitar`, `ultimate-guitar-bass`, `…-quiet`, `../tab`, `../tab-edit` | download guitar or bass tabs | `mpdj tabs [--bass] [--open]` (a search link; scraping no longer works) |
| `truename-fix` | rename folders to the artist name Last.fm prefers | dropped |
| `variables` | shared settings | `~/.config/mpdj/config.toml` |

`mpdj import-legacy` reads the old `_lyrics/`, `__similar/` and loved-playlist data, so nothing
fetched by these scripts is lost.

### Finding new music

| Old | What it did | Now |
|---|---|---|
| `suggestions`, `suggested-artists`, `lastfm-rec`, `lastfm-suggest`, `album-check` | similar artists or albums you don't own | `mpdj suggest` (HTML report) |
| `SXM-darkwave` | scrape darkwave radio playlists into a want list | dropped |
| `list-to-playlist`, `playlist-from-list`, `youtube-get-songs`, `youtube-get-songs.save` | turn a text list into a playlist; look up missing songs on YouTube | dropped |

### Server and sound

| Old | What it did | Now |
|---|---|---|
| `mpdrestart`, `mpdwatcher` | restart MPD and reload the queue when it died | systemd user service with `Restart=on-failure`; `contrib/wslg/wslg-audio-watchdog` on WSL |
| `mpdupdate` | rescan the library and email a "new music" playlist | `mpc update` |
| `mpdnotify.1` (pbrisbin) | desktop notification on song change | dropped |
| `basement-on/off`, `kitchen-on/off`, `mute-mpd`, `mute-cozy`, `interupt`, `beep.wav` | room speakers, muting, a doorbell chime, the rating confirmation beep | dropped: tied to that machine's hardware |

### Library and tag maintenance

`apetag` (Jeremy Evans, MIT), `apewipe`, `tagaggeddon`, `tagfix_2.4to2.3_remove-v1`,
`tagedit`, `covercheck`, `nocover`, `console-album-cover`, `scan-dir-cleanup`,
`file-checker`, `playlist-verifier`, `playlist-verifier2` and the empty `mp3.list`
cleaned up tags, cover art, folders and playlist paths. They're out of scope for mpdj, which
never writes to the music library. Use a tag editor such as beets, Picard or Kid3.

### Third-party tools that were installed here

| Folder | What it is | Now |
|---|---|---|
| `mpdcron/` | hooks and config for mpdcron (Ali Polatel): scrobbling and event scripts | `mpdscribble` (set up by `install.sh`) and the mpdj daemon |
| `lastfmpdqc/` | lastfmpdqc (2007): auto-queue from Last.fm similar artists | the daemon auto-queue |
| `mpd-mela/` | MPD-Mela (PHP): playlists from your Last.fm data | `mpdj loved-sync`, `mpdj suggest` |
| `playlistbuilder/` | playlistbuilder (Ruby): playlists from Last.fm similar tracks | `mpdj more similar` |
| `last_to_libre/` | lastexport.py and friends: copy Last.fm history to Libre.fm | dropped |

Each keeps its original author and license header.
