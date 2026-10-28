#!/bin/bash
source /etc/myscripts/colors.sh

_MPCSTATUS=$(mpc status -f 'ARTIST:%artist%\nALBUM:%album%\nTRACK:%track%\nTITLE:%title%\nFILE:%file%\n')
#echo -e "$_MPCSTATUS"
_ARTIST=$(grep 'ARTIST:' <<< "$_MPCSTATUS" | sed 's|ARTIST:||')
_ALBUM=$(grep 'ALBUM:' <<< "$_MPCSTATUS" | sed 's|ALBUM:||')
_TRACK=$(grep 'TRACK:' <<< "$_MPCSTATUS" | sed 's|TRACK:||')
_TITLE=$(grep 'TITLE:' <<< "$_MPCSTATUS" | sed 's|TITLE:||')
_CONSUME=$(grep consume: <<< "$_MPCSTATUS" | cut -c 57-68 | sed -r 's|\s*$||g')
_VOLUME=$(grep volume:  <<< "$_MPCSTATUS" | cut -c 1-12 | sed -r 's|\s*$||g')
_REPEAT=$(grep repeat: <<< "$_MPCSTATUS" | cut -c 15-25 | sed -r 's|\s*$||g')
_RANDOM=$(grep random: <<< "$_MPCSTATUS" | cut -c 29-40 | sed -r 's|\s*$||g')
_SINGLE=$(grep single: <<< "$_MPCSTATUS" | cut -c 43-55 | sed -r 's|\s*$||g')
_STATUS=$(grep -E '(playing|paused)' <<< "$_MPCSTATUS" | cut -c1-10)
_STATUS=${_STATUS//[\[\]]}
if [ -z $_STATUS ] ; then
        _STATUS='Stopped'
fi
_STATUS=$(sed 's|^|status: |' <<< "$_STATUS")

pygNotify.py -n "gargoyle2" -t "$_ARTIST"$'\n'"$_TITLE" -p "brimstone" -H 192.168.0.21 -m "$_STATUS  "$'\n'"[$_CONSUME $_RANDOM]" -P 3
