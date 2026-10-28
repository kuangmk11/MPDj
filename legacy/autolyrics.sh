#!/bin/bash
source /etc/myscripts/colors.sh
clear
_DARTIST="$(mpc current -f '%artist%')"
_DALBUM="$(mpc current -f '%title%')"
_ARTIST=${_DARTIST//[-+=.,]}
_ALBUM=${_DALBUM//[-+=.,]}
FILENAME=/storage/dd1/lyrics/"$_ARTIST"/"$_ARTIST - $_ALBUM".txt
clear
if [ -e "$FILENAME" ] ; then
        exec cat "$FILENAME"
	echo ""
else
	bash /etc/myscripts/mpd/lyrics/autolyricwiki.sh "$_ARTIST" "$_ALBUM"
fi
mpc current --wait
echo ""
#bash /etc/myscripts/mpd/autolyrics.sh &
exit


