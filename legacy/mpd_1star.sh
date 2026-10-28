#!/bin/bash
source /etc/myscripts/colors.sh
file=$(mpc current -f %file%)
mpc sticker "$file" set rating 1
eyeD3 --user-text-frame MYRATING:1 "/storage/dd1/mp3/$file"
if [[ $1 = -t ]] ; then
	/etc/myscripts/mpd/mpdskipper -t
else
	/etc/myscripts/mpd/mpdskipper -b
fi
beep -f 1000 -l 500
aplay /etc/myscripts/cmus_app/beep.wav
exit 0
