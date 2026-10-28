#!/bin/bash
if echo "$*" | grep -v '\-\-nocolors' ; then
	source /etc/myscripts/colors.sh
fi
source /etc/myscripts/mpd/lyrics/variables
clear

#delete and edit
if [[ $1 = -d ]]
then
echo $(date "+%b %d %H:%M")" : lyrics.sh: -d $_LYRFILE" >> /var/log/mpd.log
rm "$_LYRFILE"
nano "$_LYRFILE"
chmod 777 "$_LYRFILE" >/dev/null 2>&1
exit
fi

#edit
if [[ $1 = -e ]]
then
nano "$_LYRFILE"
chmod 777 "$_LYRFILE" >/dev/null 2>&1
exit
fi

#manual search
if [[ $1 = -m ]]
then
        echo $reset $black $redback
        read -e -p "Artist:$reset$yellow" _ARTIST
        echo $reset $black $redback
        read -e -p "Title:$reset$yellow" _TITLE
        echo $reset
	_ARTIST=$(echo "$_ARTIST" | perl -ne 'print lc')
	_TITLE=$(echo "$_TITLE" | perl -ne 'print lc')
	_ARTIST=${_ARTIST//&/and}
	_ALBUM=${_ALBUM//&/and}
	_TITLE=${_TITLE//&/and}
	_PATH_ARTIST=${_ARTIST//[\'\"\?:+=.,]}
	_PATH_ALBUM=${_ALBUM//[\'\"\?:+=.,]}
	_PATH_TITLE=${_TITLE//[\'\"\?:+=.,]}
	_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.txt"
	lrc_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.lrc"
	_LYRPATH="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST"
	_URL="${_TPL//"<artist>"/$_ARTIST}"
	_URL="${_URL//"<title>"/$_TITLE}"
fi


echo $red
echo "$_ARTIST"
echo "$_TITLE" $reset $white
#echo "───────────────────┐"
#echo "         ┌─────────┘"
#echo "         ↓          " 
echo $reset $cyan

if [ -e "$lrc_LYRFILE" ] ; then
	cat "$lrc_LYRFILE" | sed -E 's/^\[.+]//' | sed '/./,$!d'
	#sed -E 's/^\[.+]//' "$lrc_LYRFILE"
	echo $reset
	exit 0
elif [ -e "$_LYRFILE" ] ; then
	chmod 777 "$_LYRFILE" >/dev/null 2>&1
       	cat "$_LYRFILE"
	echo ""
	echo $red"இ"$green"ڰۣ-ڰۣ—"
else
	echo $reset $black $whiteback
	echo "No Local Lyrics - Fetching...    "
	echo $reset
	rm "$_file" >> /dev/null 2>&1
	touch "$_file"

	if [ -s "$_LYRFILE" ] ; then
        	echo "already exists"
	else
	        echo "makeitpersonal.co"
		_LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
		if [ "$_LYRICS" = "$_SRY" ]; then
			echo "songmeanings"
			_LYRICS=$(/etc/myscripts/mpd/lyrics/song-meanings "$_ARTIST" "$_TITLE")
		fi
	        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
			mkdir "$_LYRPATH" >/dev/null 2>&1
	                echo "$_LYRICS" > "$_LYRFILE"
	                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
		else
	                echo "lyricswiki"
			ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_ARTIST" "$_TITLE" 2> /dev/null >> "$_file"
		 	if [ -s "$_file" ] ; then
	                        echo ""
	                else
	                        echo $reset
	                        echo $black $whiteback $bold
	                        echo "No Lyrics Found - Search Manually"
	                        echo $reset $black $redback
	                        read -e -p "Artist:$reset$yellow" -i "$_ARTIST" _3ARTIST
	                        echo $reset $black $redback
	                        read -e -p "Title:$reset$yellow" -i "$_TITLE" _2TITLE
	                        _3ARTIST=$(echo "$_3ARTIST" | perl -ne 'print lc')
				_2TITLE=$(echo "$_2TITLE" | perl -ne 'print lc')
				echo $reset $cyan
	                        _URL="${_TPL//"<artist>"/$_3ARTIST}"
	                        _URL="${_URL//"<title>"/$_2TITLE}"
				echo "makeitpersonal.co"
	                        _LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
	                        if [ "$_LYRICS" != "$_SRY" ]; then
	                                mkdir "$_LYRPATH" >/dev/null 2>&1
	                                echo "$_LYRICS" > "$_LYRFILE"
	                                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
	                        else
	                                echo "lyricswiki"
					ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_3ARTIST" "$_2TITLE" 2> /dev/null >> "$_file"
				fi
	                fi
	        fi
	fi
	if [ -s "$_LYRFILE" ] ; then
		chmod 777 "$_LYRFILE" >/dev/null 2>&1
	        touch "$_LYRFILE"
	elif [ -s "$_file" ] ; then
	        mkdir "$_LYRPATH" >> /dev/null 2>&1
	        sed -i "s/&#8217;/'/" "$_file"
	        sed -i "s#<b>##" "$_file"
	        sed -i "s#<i>##" "$_file"
	        sed -i "s#</b>##" "$_file"
	        sed -i "s#</i>##" "$_file"
	        sed -i "s|script>|'$'\n|gi" "$_file"
	        sed -i '/showAsyncAd/d' "$_file"
		#tail -n +2 "$_file" > "$_LYRFILE"
		cat "$_file" > "$_LYRFILE"
	        # do something as file has data
	else
	        clear
		read -p "Search and Edit? " -n 1 -r
		echo    # (optional) move to a new line
		if [[ $REPLY =~ ^[Yy]$ ]]
		then
			echo "$_LYRFILE"
	                mkdir "$_LYRPATH" >> /dev/null 2>&1
			#lynx "https://www.google.com/search?q=%22$_ARTIST%22+%22$_TITLE%22+lyrics&ie=utf-8&oe=utf-8"
			gedit "$_LYRFILE" >/dev/null 2>&1 &
			geditPID=$!
			firefox "https://www.google.com/search?q=%22$_ARTIST%22+%22$_TITLE%22+lyrics&ie=utf-8&oe=utf-8" >/dev/null 2>&1 &
			ffPID=$!
			wait $geditPID
			kill $ffPID >/dev/null 2>&1
			#nano "$_LYRFILE"
		fi
	fi
	minimumsize=2
	actualsize=$(wc -c "$_LYRFILE" 2> /dev/null | cut -f 1 -d ' ' )
	if [[ $actualsize -ge $minimumsize ]]; then
    		touch "$_LYRFILE"
	else
    		rm "$_LYRFILE" >/dev/null 2>&1
	fi
	if [ -s "$_LYRFILE" ]
	then
		chmod 777 "$_LYRFILE" >/dev/null 2>&1
	        cat "$_LYRFILE"
	else
	        echo "$_ARTIST - $_TITLE" >> /var/log/lyrics.log
	        sort -u /var/log/lyrics.log -o /var/log/lyrics.log
	fi
	rm "$_file" > /dev/null 2>&1
	echo ""
fi
echo $reset
