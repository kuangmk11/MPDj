#!/bin/bash
#
#  (c) 2004-2008 The Music Player Daemon Project
#  http://www.musicpd.org/
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

#
#
_file=/tmp/lyrics.tmp
C1=${1//[-+=.,]}
C2=${2//[-+=.,]}
FILENAME=/storage/dd1/mp3/_lyrics/"$C1"/"$C1 - $C2".txt
rm /tmp/lyrics.tmp >> /dev/null 2>&1
touch /tmp/lyrics.tmp
ruby /usr/lib/ncmpc/lyrics/.support/20-lyricwiki.rb "$C1" "$C2" >> /tmp/lyrics.tmp
sed -i "s|script>|'$'\n|gi" /tmp/lyrics.tmp
if [ -s "$_file" ]
then
	mkdir /storage/dd1/mp3/_lyrics/"$C1" >> /dev/null 2>&1
	tail -n +2 /tmp/lyrics.tmp > "$FILENAME"
	exec cat "$FILENAME"
        # do something as file has data
else
	echo "No Lyrics Found"
	echo $FILENAME
	#mkdir "/storage/dd1/mp3/_lyrics/$C1" >> /dev/null 2>&1
	#nano "$FILENAME"
        # do something as file is empty 
fi
#tail -n +2 /tmp/lyrics.tmp 
rm /tmp/lyrics.tmp >> /dev/null 2>&1

