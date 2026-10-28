#!/bin/bash
if [ ! -z $TERM ] ; then
	source /etc/myscripts/colors.sh
fi
_TPL='http://makeitpersonal.co/lyrics?artist=<artist>&title=<title>'
_SRY="Sorry, We don't have lyrics for this song yet."
_TMP_FILE=/tmp/lyrics.tmp
if [[ $1 = -p ]] ; then
	_FILEPATH="/storage/dd1/mp3/$(mpc current -f %file%)"
	_PATH=$(dirname "$_FILEPATH")
else
	[ "$1" ] && _PATH="$1" || _PATH=$PWD
fi

cd "$_PATH"

for _FILE in {*.mp3,*.m4a}; do
    if [[ -r "$_FILE" ]]; then
        rm "$_TMP_FILE" >/dev/null 2>&1
	_ARTIST=$(eyeD3 --no-color "$_FILE" 2> /dev/null | grep '^artist: ' | sed 's/^artist: //' | sed 's|\/|_|' | perl -ne 'print lc')
        _TITLE=$(eyeD3 --no-color "$_FILE" 2> /dev/null | grep '^title: ' | sed 's/^title: //' | sed 's|\/|_|' | sed -r 's|\s*\(.+\)||g' | sed -r 's|\s*\[.+\]||g' | perl -ne 'print lc')
	_ARTIST=${_ARTIST//&/and}
	_ARTIST=${_ARTIST//\./}
	_ARTIST=${_ARTIST//\?/}
	_TITLE=${_TITLE//&/and}
	_TITLE=${_TITLE//\?/}
	_PATH_ARTIST=${_ARTIST//[\?\:\+\=\.,]}
	_PATH_ARTIST=${_PATH_ARTIST//\'/_}
	_PATH_ARTIST=${_PATH_ARTIST//\"/_}
	_PATH_ARTIST=$(echo "$_PATH_ARTIST" | sed -r 's/christian death.+/christian death/' | sed -r 's/^warsaw$/joy division/')
	_PATH_TITLE=${_TITLE//[\?\:\+\=\.,]}
	_PATH_TITLE=${_PATH_TITLE//\'/_}
	_2ARTIST=$(echo "$_ARTIST" | sed -r 's/christian death.+/christian death/' | sed -r 's/^warsaw$/joy division/' | sed -r 's/^fire \+ ice$/fire %2B ice/')
	echo ""
	echo $ltblue"$_2ARTIST - $_TITLE"$reset

        _URL="${_TPL//"<artist>"/$_2ARTIST}"
        _URL="${_URL//"<title>"/$_TITLE}"
	_LYRPATH="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST"
	_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.txt"


        if [ -s "$_LYRFILE" ] ; then
		echo $yellow"already exists"$reset
		chmod 777 "$_LYRFILE" >/dev/null 2>&1
	elif grep -q "$_URL" /home/ono/.lyric-url-tried.txt; then
                echo $yellow"Tried that URL today and found nothing"$reset
	else
		echo "trying makeitpersonal.co"

		_LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
		echo "$_URL" >> /home/ono/.lyric-url-tried.txt
        	if [ "$_LYRICS" != "$_SRY" ]; then
           		echo "got something"
			mkdir "$_LYRPATH" >/dev/null 2>&1
			echo "$_LYRICS" > "$_LYRFILE"
			echo $green"SUCCESS!"$reset
			#eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
		fi
		if [ ! -s "$_LYRFILE" ] ; then
            		echo "trying lyricwiki"
			ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_2ARTIST" "$_TITLE" 2> /dev/null >> "$_TMP_FILE"
	               	if [ -s "$_TMP_FILE" ] ; then
	                      	echo "got something"
				mkdir "$_LYRPATH" >> /dev/null 2>&1
                        	sed -i "s/&#8217;/'/" "$_TMP_FILE"
                        	sed -i "s#<b>##" "$_TMP_FILE"
                        	sed -i "s#<i>##" "$_TMP_FILE"
                        	sed -i "s#</b>##" "$_TMP_FILE"
                        	sed -i "s#</i>##" "$_TMP_FILE"
                        	sed -i "s|script>|'$'\n|gi" "$_TMP_FILE"
                        	sed -i '/showAsyncAd/d' "$_TMP_FILE"
				tail -n +1 "$_TMP_FILE" > "$_LYRFILE"
				rm "$_TMP_FILE"
				echo $green"SUCCESS!"$reset
                	fi
		fi
		if [ ! -s "$_LYRFILE" ] ; then
			echo "trying songmeanings"
			_LYRICS=$(/etc/myscripts/mpd/lyrics/song-meanings "$_ARTIST" "$_TITLE")
			if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                        	mkdir "$_LYRPATH" >/dev/null 2>&1
                        	echo "$_LYRICS" > "$_LYRFILE"
				echo $green"SUCCESS!"$reset
			fi
		fi
		if [ ! -s "$_LYRFILE" ] ; then
                        echo "trying songlyrics"
                        _LYRICS=$(/etc/myscripts/mpd/lyrics/song-lyrics "$_ARTIST" "$_TITLE")
                        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                                mkdir "$_LYRPATH" >/dev/null 2>&1
                                echo "$_LYRICS" > "$_LYRFILE"
                                echo $green"SUCCESS!"$reset
                        fi
                fi
		if [ ! -s "$_LYRFILE" ] ; then
                        echo "trying songtexte"
                        _LYRICS=$(/etc/myscripts/mpd/lyrics/songtexte "$_ARTIST" "$_TITLE")
                        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                                mkdir "$_LYRPATH" >/dev/null 2>&1
                                echo "$_LYRICS" > "$_LYRFILE"
                                echo $green"SUCCESS!"$reset
                        fi
                fi
                if [ ! -s "$_LYRFILE" ] ; then
                        echo "trying darklyrics"
                        _LYRICS=$(/etc/myscripts/mpd/lyrics/darklyrics "$_ARTIST" "$_TITLE")
                        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                                mkdir "$_LYRPATH" >/dev/null 2>&1
                                echo "$_LYRICS" > "$_LYRFILE"
                                echo $green"SUCCESS!"$reset
                        fi
                fi

		if [ -s "$_LYRFILE" ] ; then
			touch "$_LYRFILE"
			chmod 777 "$_LYRFILE" >/dev/null 2>&1
		else
			echo $red"No lyrics found..."$reset
			echo "$_ARTIST - $_TITLE" >> /var/log/lyrics.log
        		sort -u /var/log/lyrics.log -o /var/log/lyrics.log
        	fi
	fi
    fi
done
#aplay -q /etc/myscripts/cmus_app/beep.wav
cd "$OLDPWD"
