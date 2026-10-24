#!/usr/bin/env bash
# Set up MPD + mpdj + ncmpcpp on a new machine (Ubuntu/Debian, with systemd; WSL or desktop).
# Safe to re-run: existing config files are kept; only the mpdj parts are added or refreshed.
#
#   ./install.sh --music-dir /mnt/mp3/MP3 --share //10.10.10.4/Music --mount /mnt/mp3
#   ./install.sh --music-dir ~/Music --lastfm-key KEY --lastfm-user NAME
#   ./install.sh --db ~/mpdj.db        # bring ratings, bans, history and lyrics along
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MUSIC_DIR="" SHARE="" MOUNT="/mnt/mp3" LFM_KEY="${LASTFM_API_KEY:-}" LFM_USER="" DB="" APT=1 LINGER=0 SCROBBLE=1

usage() {
    sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
    cat <<'EOF'

Options:
  --music-dir DIR      the music folder (MPD's music_directory); asked for if not given
  --share //HOST/NAME  mount this SMB share read-only at --mount (needs sudo; asks for the login)
  --mount DIR          where to mount --share (default /mnt/mp3)
  --lastfm-key KEY     Last.fm API key (or set LASTFM_API_KEY); needed for similar artists
  --lastfm-user NAME   Last.fm username (for `loved-sync` and `rate 5`)
  --db FILE            copy an mpdj.db from another machine (ratings, bans, history, lyrics)
  --no-scrobble        don't set up Last.fm scrobbling (mpdscribble)
  --linger             start MPD at boot, not at first login
  --no-apt             don't install packages
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --music-dir) MUSIC_DIR=$2; shift ;;
        --share) SHARE=$2; shift ;;
        --mount) MOUNT=$2; shift ;;
        --lastfm-key) LFM_KEY=$2; shift ;;
        --lastfm-user) LFM_USER=$2; shift ;;
        --db) DB=$2; shift ;;
        --linger) LINGER=1 ;;
        --no-scrobble) SCROBBLE=0 ;;
        --no-apt) APT=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
    esac
    shift
done

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok() { printf '   %s\n' "$*"; }
WSL=0; grep -qi microsoft /proc/version 2>/dev/null && WSL=1

if ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "systemd user services aren't running. On WSL, add this to /etc/wsl.conf and restart WSL:" >&2
    printf '  [boot]\n  systemd=true\n' >&2
    exit 1
fi

if [[ -z $MUSIC_DIR ]]; then
    default=""; [[ -n $SHARE ]] && default=$MOUNT
    read -rp "Music folder${default:+ [$default]}: " MUSIC_DIR
    MUSIC_DIR=${MUSIC_DIR:-$default}
fi
[[ -z $MUSIC_DIR ]] && { echo "need --music-dir" >&2; exit 2; }
MUSIC_DIR=${MUSIC_DIR/#\~/$HOME}

# --- packages -----------------------------------------------------------------
if (( APT )); then
    say "Packages"
    pkgs=(mpd mpc ncmpcpp curl)
    [[ -n $SHARE ]] && pkgs+=(cifs-utils)
    (( SCROBBLE )) && pkgs+=(mpdscribble)
    missing=(); for p in "${pkgs[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if (( ${#missing[@]} )); then
        sudo apt-get update -q && sudo apt-get install -y "${missing[@]}"
    fi
    ok "installed: ${pkgs[*]}"
    # Debian's mpd package starts a system-wide MPD on port 6600; we run it per user instead.
    if systemctl is-enabled -q mpd.service 2>/dev/null || systemctl is-enabled -q mpd.socket 2>/dev/null \
       || systemctl is-active -q mpd.service 2>/dev/null; then
        sudo systemctl disable --now mpd.service mpd.socket
        ok "turned off the system-wide MPD (it would take port 6600)"
    fi
    # Same for the package's system-wide scrobbler: we run it as the user, next to MPD.
    if (( SCROBBLE )) && { systemctl is-enabled -q mpdscribble.service 2>/dev/null \
                           || systemctl is-active -q mpdscribble.service 2>/dev/null; }; then
        sudo systemctl disable --now mpdscribble.service
        ok "turned off the system-wide mpdscribble"
    fi
fi

# --- network share --------------------------------------------------------------
if [[ -n $SHARE ]]; then
    say "Share $SHARE -> $MOUNT (read-only)"
    if grep -qsE "^[^#]*[[:space:]]$MOUNT[[:space:]]" /etc/fstab; then
        ok "already in /etc/fstab"
    else
        cred=/root/.smb-$(basename "$MOUNT")
        read -rp "   SMB username: " smb_user
        read -rsp "   SMB password: " smb_pass; echo
        # The login goes in a root-only file, not in fstab (some setups commit /etc to git).
        printf 'username=%s\npassword=%s\n' "$smb_user" "$smb_pass" | sudo tee "$cred" >/dev/null
        sudo chmod 600 "$cred"
        sudo mkdir -p "$MOUNT"
        echo "$SHARE $MOUNT cifs ro,credentials=$cred,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=30 0 0" \
            | sudo tee -a /etc/fstab >/dev/null
        sudo systemctl daemon-reload
        sudo systemctl restart "$(systemd-escape -p --suffix=automount "$MOUNT")" || true
        ok "added to /etc/fstab (login in $cred)"
    fi
    if ls "$MOUNT" >/dev/null 2>&1; then ok "mounted: $(ls "$MOUNT" | head -5 | tr '\n' ' ')"; else
        echo "   couldn't open $MOUNT; check the share and login, then re-run" >&2; fi
fi
[[ -d $MUSIC_DIR ]] || echo "   warning: $MUSIC_DIR doesn't exist (yet)" >&2

# --- mpdj itself -----------------------------------------------------------------
say "mpdj"
UV=$(command -v uv || echo "$HOME/.local/bin/uv")
if [[ ! -x $UV ]]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    UV=$HOME/.local/bin/uv
fi
"$UV" tool install -q -e "$REPO" --force   # editable: `git pull` updates it
ok "installed $HOME/.local/bin/mpdj (from $REPO)"
export PATH=$HOME/.local/bin:$PATH

# --- config files -----------------------------------------------------------------
say "Config"
mkdir -p ~/.config/mpd/playlists ~/.config/mpdj ~/.config/ncmpcpp ~/.lyrics ~/.config/systemd/user

if [[ ! -f ~/.config/mpd/mpd.conf ]]; then
    if (( WSL )); then
        out='audio_output {\n    type    "pulse"\n    name    "WSLg"\n    server  "unix:/mnt/wslg/PulseServer"\n}'
    else
        out='audio_output {\n    type    "pulse"\n    name    "Speakers"\n}'
    fi
    sed -e "s|^music_directory .*|music_directory     \"$MUSIC_DIR\"|" \
        -e '/^# WSLg provides/,$d' "$REPO/contrib/mpd/mpd.conf" > ~/.config/mpd/mpd.conf
    printf '%b\n' "$out" >> ~/.config/mpd/mpd.conf
    ok "wrote ~/.config/mpd/mpd.conf"
else
    ok "kept ~/.config/mpd/mpd.conf"
fi

[[ -f ~/.config/mpdj/config.toml ]] || mpdj init >/dev/null
python3 - "$HOME/.config/mpdj/config.toml" "$MUSIC_DIR" "$LFM_KEY" "$LFM_USER" <<'EOF'
import re, sys
path, music, key, user = sys.argv[1:]
s = open(path).read()
def put(name, value, only_if_empty=False):
    global s
    m = re.search(rf'^{name} = "(.*?)"', s, re.M)
    if m and value and not (only_if_empty and m.group(1)):
        s = s[:m.start()] + f'{name} = "{value}"' + s[m.end():]
put("music_dir", music)
put("api_key", key)
put("username", user)
open(path, "w").write(s)
if not re.search(r'^api_key = "\S+', s, re.M):
    print("   no Last.fm API key yet: similar-artist queueing needs one (https://www.last.fm/api/account/create)")
EOF
ok "~/.config/mpdj/config.toml: music_dir = $MUSIC_DIR"

if [[ ! -f ~/.config/ncmpcpp/config ]]; then
    { echo "mpd_music_dir = $MUSIC_DIR"
      echo "store_lyrics_in_song_dir = no"
      grep -v '^## set this\|^# mpd_music_dir\|^## mpdj-related' "$REPO/contrib/ncmpcpp/config"; } > ~/.config/ncmpcpp/config
    ok "wrote ~/.config/ncmpcpp/config"
else
    ok "kept ~/.config/ncmpcpp/config"
fi
# key bindings: keep the user's own, replace only the mpdj block
b=~/.config/ncmpcpp/bindings; touch "$b"
cmp -s "$b" "$REPO/contrib/ncmpcpp/bindings" && : > "$b"   # an older plain copy
sed -i '/^## >>> mpdj/,/^## <<< mpdj/d' "$b"
{ echo "## >>> mpdj (managed by $REPO/install.sh)"; cat "$REPO/contrib/ncmpcpp/bindings"; echo "## <<< mpdj"; } >> "$b"
ok "ncmpcpp key bindings (Alt+key) in $b"

# Last.fm scrobbling. mpdscribble only needs the username and password (it has its own
# API key); the password is stored as its MD5 hash in a file only the user can read.
SC=~/.config/mpdscribble/mpdscribble.conf
if (( SCROBBLE )) && ! command -v mpdscribble >/dev/null; then
    echo "   mpdscribble isn't installed (sudo apt install mpdscribble), skipping scrobbling" >&2
    SCROBBLE=0
fi
if (( SCROBBLE )) && [[ -f $SC ]]; then
    ok "kept $SC"
elif (( SCROBBLE )); then
    mkdir -p ~/.config/mpdscribble ~/.cache/mpdscribble
    default_user=${LFM_USER:-$(sed -n 's/^username = "\([^"]*\)".*/\1/p' ~/.config/mpdj/config.toml)}
    read -rp "   Last.fm username for scrobbling${default_user:+ [$default_user]}: " s_user
    s_user=${s_user:-$default_user}
    read -rsp "   Last.fm password (saved as an MD5 hash): " s_pass; echo
    if [[ -n $s_user && -n $s_pass ]]; then
        hash=$(printf %s "$s_pass" | md5sum | cut -d' ' -f1)
        unset s_pass
        ( umask 077
          printf '%s\n' \
            "# mpdscribble: scrobbles MPD plays. Written by $REPO/install.sh. Keep private." \
            "host = localhost" "port = 6600" "log = -" "verbose = 1" "" \
            "[last.fm]" "url = https://post.audioscrobbler.com/" \
            "username = $s_user" "password = $hash" \
            "journal = $HOME/.cache/mpdscribble/lastfm.journal" > "$SC" )
        ok "wrote $SC (plays made while offline are sent later)"
    else
        echo "   no username/password: skipping scrobbling (re-run to set it up)" >&2
        SCROBBLE=0
    fi
fi

# --- services ---------------------------------------------------------------------
say "Services"
U=~/.config/systemd/user
mkdir -p "$U/mpd.service.d"
cat > "$U/mpd.service.d/wait-for-music.conf" <<EOF
# If MPD starts before the music folder is mounted it fails every file with ELOOP
# ("Too many levels of symbolic links"). Wait for it and retry.
[Unit]
StartLimitIntervalSec=0

[Service]
ExecStartPre=/usr/bin/test -d "$MUSIC_DIR"
Restart=on-failure
RestartSec=10
EOF
cp "$REPO/contrib/systemd/mpdj.service" "$U/"
units=(mpd.service mpdj.service)
if (( SCROBBLE )); then
    cp "$REPO/contrib/mpdscribble/mpdscribble.service" "$U/"
    units+=(mpdscribble.service)
fi
if (( WSL )); then
    cp "$REPO/contrib/wslg/wslg-audio-watchdog" ~/.local/bin/
    cp "$REPO/contrib/wslg/wslg-audio-watchdog."{service,timer} "$U/"
    units+=(wslg-audio-watchdog.timer)
fi
systemctl --user daemon-reload
systemctl --user enable -q "${units[@]}"
(( LINGER )) && sudo loginctl enable-linger "$USER" && ok "services start at boot"

if [[ -n $DB ]]; then
    systemctl --user stop mpdj.service 2>/dev/null || true
    d=~/.local/share/mpdj; mkdir -p "$d"
    [[ -f $d/mpdj.db ]] && cp "$d/mpdj.db" "$d/mpdj.db.before-import"
    cp "$DB" "$d/mpdj.db"; rm -f "$d/mpdj.db-wal" "$d/mpdj.db-shm"
    ok "copied $DB -> $d/mpdj.db"
fi
systemctl --user restart mpd.service
systemctl --user restart mpdj.service
(( SCROBBLE )) && systemctl --user restart mpdscribble.service
(( WSL )) && systemctl --user start wslg-audio-watchdog.timer
ok "running: ${units[*]}"

# --- first scan -------------------------------------------------------------------
say "Music database"
for _ in 1 2 3 4 5; do mpc -q status >/dev/null 2>&1 && break; sleep 2; done
songs=$(mpc stats 2>/dev/null | awk '/^Songs:/{print $2}')
if [[ ${songs:-0} -eq 0 ]]; then
    mpc -q update && ok "scanning $MUSIC_DIR in the background (a large library takes a while; \`mpc stats\` shows progress)"
else
    ok "$songs songs (run \`mpc update\` after adding music)"
fi
mpc -q consume on && ok "consume mode on (mpdj refills the queue as songs are played)"

say "Done"
cat <<EOF
   Try:  mpdj artist <name>   ·   mpdj status   ·   ncmpcpp (Alt+S = more similar)
   Logs: journalctl --user -u mpdj -f
EOF
