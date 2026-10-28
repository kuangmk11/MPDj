#!/bin/bash
_file=/tmp/lyrics.tmp
_ARTIST=${1//[+=.,]}
_TITLE=${2//[+=.,]}
_2ARTIST=$(echo "$_ARTIST" | sed -r 's/Christian Death.+/Christian Death/')
_TPL='http://makeitpersonal.co/lyrics?artist=<artist>&title=<title>'
_SRY="Sorry, We don't have lyrics for this song yet."
_URL="${_TPL//"<artist>"/$_2ARTIST}"
_URL="${_URL//"<title>"/$_TITLE}"
_LYRPATH="/storage/dd1/mp3/_lyrics/$_ARTIST"
_LYRFILE="/storage/dd1/mp3/_lyrics/$_ARTIST/$_ARTIST - $_TITLE.txt"

rm /tmp/lyrics.tmp >> /dev/null 2>&1
touch /tmp/lyrics.tmp

_LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
if [ "$_LYRICS" != "$_SRY" ]; then
	mkdir "$_LYRPATH" >/dev/null 2>&1
        echo "$_LYRICS" > "$_LYRFILE"
        #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
else
        ruby /etc/myscripts/mpd/lyrics/20-lyricwiki.rb "$_2ARTIST" "$_TITLE" 2> /dev/null >> /tmp/lyrics.tmp
	if [ -s "$_file" ] ; then
        	mkdir /storage/dd1/mp3/_lyrics/"$_ARTIST" >> /dev/null 2>&1
        	sed -i "s/&#8217;/'/" /tmp/lyrics.tmp
        	sed -i "s#<b>##" /tmp/lyrics.tmp
        	sed -i "s#<i>##" /tmp/lyrics.tmp
        	sed -i "s#</b>##" /tmp/lyrics.tmp
        	sed -i "s#</i>##" /tmp/lyrics.tmp
        	sed -i "s|script>|'$'\n|gi" /tmp/lyrics.tmp
        	tail -n +2 /tmp/lyrics.tmp > "$_LYRFILE"
	else
        	touch /tmp/lyrics.tmp
	fi

fi
if [ -s "$_LYRFILE" ] ; then
	touch /tmp/lyrics.tmp
else
        echo "$_2ARTIST - $_TITLE" >> /var/log/lyrics.log
        sort -u /var/log/lyrics.log -o /var/log/lyrics.log
fi
rm /tmp/lyrics.tmp >/dev/null 2>&1
