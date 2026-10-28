#!/bin/bash
source /etc/myscripts/colors.sh
_file=/tmp/lyrics.tmp
_ARTIST=${1//[+=.,]}
_TITLE=${2//[+=.,]}
_2ARTIST=$(echo "$_ARTIST" | sed -r 's/Christian Death.+/Christian Death/')
_URL="${_TPL//"<artist>"/$_2ARTIST}"
_URL="${_URL//"<title>"/$_TITLE}"
_LYRPATH="/storage/dd1/mp3/_lyrics/$_ARTIST"
_LYRFILE="/storage/dd1/mp3/_lyrics/$_ARTIST/$_ARTIST - $_TITLE.txt"

rm /tmp/lyrics.tmp >> /dev/null 2>&1
touch /tmp/lyrics.tmp

if [ -e "$_LYRFILE" ] ; then
        echo "already exists"
else
        _LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
        if [ "$_LYRICS" != "$_SRY" ]; then
                mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
         else
		ruby /etc/myscripts/mpd/lyrics/20-lyricwiki.rb "$_2ARTIST" "$_TITLE" 2> /dev/null >> /tmp/lyrics.tmp
		if [ -s "$_file" ] ; then
        		echo ""
		else
        		echo $reset
        		echo $black $whiteback $bold
        		echo "No Lyrics Found - Search Manually"
        		echo $reset $black $redback
        		read -e -p "Artist:$reset$yellow" -i "$_2ARTIST" _3ARTIST
        		echo $reset $black $redback
        		read -e -p "Title:$reset$yellow" -i "$_TITLE" _2TITLE
        		echo $reset $cyan
			_URL="${_TPL//"<artist>"/$_3ARTIST}"
			_URL="${_URL//"<title>"/$_2TITLE}"
			_LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
			if [ "$_LYRICS" != "$_SRY" ]; then
                		mkdir "$_LYRPATH" >/dev/null 2>&1
                		echo "$_LYRICS" > "$_LYRFILE"
                		#eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
         		else
                		ruby /etc/myscripts/mpd/lyrics/20-lyricwiki.rb "$_3ARTIST" "$_2TITLE" 2> /dev/null >> /tmp/lyrics.tmp
			fi
		fi
	fi
fi
if [ -e "$_LYRFILE" ] ; then
	touch "$_LYRFILE"
elif [ -s "$_file" ] ; then
        mkdir /storage/dd1/mp3/_lyrics/"$_ARTIST" >> /dev/null 2>&1
        sed -i "s/&#8217;/'/" /tmp/lyrics.tmp
        sed -i "s#<b>##" /tmp/lyrics.tmp
        sed -i "s#<i>##" /tmp/lyrics.tmp
        sed -i "s#</b>##" /tmp/lyrics.tmp
        sed -i "s#</i>##" /tmp/lyrics.tmp
	sed -i "s|script>|'$'\n|gi" /tmp/lyrics.tmp
        tail -n +2 /tmp/lyrics.tmp > "$_LYRFILE"
        # do something as file has data
else
        clear
	echo "$_LYRFILE"
        mkdir "/storage/dd1/mp3/_lyrics/$_ARTIST" >> /dev/null 2>&1
        nano "$_LYRFILE"
        # do something as file is empty
fi
if [ -s "$_LYRFILE" ]
then
	cat "$_LYRFILE"
else
	echo "$_2ARTIST - $_TITLE" >> /var/log/lyrics.log
	sort -u /var/log/lyrics.log -o /var/log/lyrics.log
fi
rm /tmp/lyrics.tmp > /dev/null 2>&1
echo ""

