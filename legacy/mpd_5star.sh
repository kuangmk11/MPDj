#!/bin/bash
source /etc/myscripts/colors.sh

if [[ $1 = -f ]] ; then
	shift
	file="$*"
else
	file=$(mpc current -f %file%)
fi
echo "$file" >> /storage/dd1/mp3/_PLAYLISTS/linux/mpdmela-lastfm-loved-tracks.m3u
echo "$file" >> /storage/dd1/mp3/_PLAYLISTS/linux/loved-master.lin.m3u
NAME=$(basename "/storage/dd1/mp3/$file")
echo $NAME
ln -s "/storage/dd1/mp3/$file" "/storage/dd1/mp3/_loved/$NAME"
mpc sticker "$file" set rating 10
eyeD3 --quiet --user-text-frame MYRATING:5 "/storage/dd1/mp3/$file"
#/etc/myscripts/mpd/lastfm-mpd-cli.py love
#/etc/myscripts/mpd/lastfm-mpd-cli.py love --lastfmusername=kuangmk11 --lastfmpassword=REDACTED_LASTFM_PASSWORD_MD5
/etc/myscripts/mpd/lastfm-mpd-cli.py love --lastfmusername=kuangmk11 --lastfmpassword=REDACTED_LASTFM_PASSWORD_MD5

if [[ $(mpc status | grep \\[playing\\]) ]] ; then
        mpc pause
	beep -f 1000 -l 500
        aplay -q /etc/myscripts/cmus_app/beep.wav -D mpd 2>&1 >> /dev/null
        mpc play
else
	beep -f 1000 -l 500
	aplay -q /etc/myscripts/cmus_app/beep.wav -D mpd 2>&1 >> /dev/null
fi


exit 0
