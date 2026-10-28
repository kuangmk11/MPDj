#!/bin/bash
source /etc/myscripts/colors.sh
file=$(mpc current -f %file%)
eyeD3 --user-text-frame MYRATING:4 "/storage/dd1/mp3/$file"
beep -f 1000 -l 500
aplay /etc/myscripts/cmus_app/beep.wav
exit 0
