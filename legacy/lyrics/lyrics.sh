#!/bin/bash
if echo "$*" | grep -v '\-\-nocolors' ; then
	source /etc/myscripts/colors.sh
fi
source /etc/myscripts/mpd/lyrics/variables
clear

#delete
if [[ $1 = -d ]]
then
#echo $(date "+%b %d %H:%M")" : lyrics.sh: -d $_LYRFILE" >> /var/log/mpd.log
rm "$_LYRFILE"
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

#FUNCTIONS
lyricswiki(){
	echo $yellow"lyricswiki"$reset
	_LYRICS=$(ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_ARTIST" "$_TITLE" 2> /dev/null)
	if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ] ; then
               	mkdir "$_LYRPATH" >> /dev/null 2>&1
               	echo "$_LYRICS" > "$_LYRFILE"
		sed -i "s/&#8217;/'/" "$_LYRFILE"
               	sed -i "s#<b>##" "$_LYRFILE"
               	sed -i "s#<i>##" "$_LYRFILE"
               	sed -i "s#</b>##" "$_LYRFILE"
               	sed -i "s#</i>##" "$_LYRFILE"
               	sed -i "s|script>|'$'\n|gi" "$_LYRFILE"
               	sed -i '/showAsyncAd/d' "$_LYRFILE"
	fi
}

songmeanings(){
	echo $yellow"songmeanings"$reset
	_LYRICS=$(/etc/myscripts/mpd/lyrics/song-meanings "$_ARTIST" "$_TITLE")
        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
		mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
		dos2unix "$_LYRFILE" >/dev/null 2>&1
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
	fi
}

makeitpersonal(){
	echo $yellow"makeitpersonal.co"$reset
	_LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
	if [ "$_LYRICS" != "$_SRY" ]; then
		mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
	fi
}

songlyrics(){
        echo $yellow"songlyrics"$reset
        _LYRICS=$(/etc/myscripts/mpd/lyrics/song-lyrics "$_ARTIST" "$_TITLE")
        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
                dos2unix "$_LYRFILE" >/dev/null 2>&1
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
        fi
}

songtexte(){
        echo $yellow"songtexte"$reset
        _LYRICS=$(/etc/myscripts/mpd/lyrics/songtexte "$_ARTIST" "$_TITLE")
        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
                dos2unix "$_LYRFILE" >/dev/null 2>&1
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
        fi
}

darklyrics(){
        echo $yellow"darklyrics"$reset
        _LYRICS=$(/etc/myscripts/mpd/lyrics/darklyrics "$_ARTIST" "$_TITLE")
        if [ ! -z "$(echo "$_LYRICS" | sed '/^\s*$/d')" ]; then
                mkdir "$_LYRPATH" >/dev/null 2>&1
                echo "$_LYRICS" > "$_LYRFILE"
                dos2unix "$_LYRFILE" >/dev/null 2>&1
                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
        fi
}

minsize(){
	minimumsize=2
	actualsize=$(wc -c "$_LYRFILE" 2> /dev/null | cut -f 1 -d ' ' )
	if [[ $actualsize -ge $minimumsize ]]; then
    		touch "$_LYRFILE"
	else
    		rm "$_LYRFILE" >/dev/null 2>&1
		sleep 1
	fi
}

translatelyric(){
	if grep -vq "|" "$_LYRFILE" ; then
		if trans -i "$_LYRFILE" | grep -q "\-> English" ; then
			echo $yellow
			read -p "Looks like it contains a foreign language.  Translate? " -n 1 -r
	        	echo $reset
                	if [[ $REPLY =~ ^[Yy]$ ]] ; then
				translyrics
			fi
		fi
	fi
}

###end FUNCTIONS

echo $red
echo "$_ARTIST"
echo "$_TITLE" $reset $white
#echo "───────────────────┐"
#echo "         ┌─────────┘"
#echo "         ↓          " 
echo $reset $cyan

#look for and display synced lyric (strip timing)
if [ -e "$lrc_LYRFILE" ] ; then
	cat "$lrc_LYRFILE" | sed -E 's/^\[.+]//' | sed '/./,$!d'
	#sed -E 's/^\[.+]//' "$lrc_LYRFILE"
	echo $reset
	exit 0
#look for and display standard lyric
elif [ -e "$_LYRFILE" ] ; then
	chmod 777 "$_LYRFILE" >/dev/null 2>&1
       	cat "$_LYRFILE"
	echo ""
	echo $red"இ"$green"ڰۣ-ڰۣ—"$reset
	translatelyric
	exit 0
#no local check the net
else
	echo $reset $black $whiteback
	echo "No Local Lyrics - Fetching...    "
	echo $reset

	if [ -s "$_LYRFILE" ] ; then
        	echo "already exists.  something must be wrong"
		echo "$_LYRFILE"
	fi
#makeitpersonal
	if [ ! -s "$_LYRFILE" ] ; then
		makeitpersonal
		minsize
	fi

#songmeanings
	if [ ! -s "$_LYRFILE" ] ; then
		songmeanings
		minsize
	fi

#songlyrics
        if [ ! -s "$_LYRFILE" ] ; then
                songlyrics
                minsize
        fi

#lyricswiki
	if [ ! -s "$_LYRFILE" ] ; then
		lyricswiki
		minsize
	fi
#songtexte
        if [ ! -s "$_LYRFILE" ] ; then
                songtexte
                minsize
        fi
#darklyrics
        if [ ! -s "$_LYRFILE" ] ; then
                darklyrics
                minsize
        fi


#if nothing found manual search
	if [ ! -s "$_LYRFILE" ] ; then
		echo
		echo "Search Was:"
		echo $red"Artist:"$reset"$_ARTIST  "$red"Title:"$reset"$_TITLE"
		echo $yellow
		read -p "Change Query and Search Again? " -n 1 -r
        	echo $reset
		echo    # (optional) move to a new line
	        if [[ $REPLY =~ ^[Yy]$ ]] ; then
			if [ ! -s "$_LYRFILE" ] ; then
		       		echo $reset
	                	echo $black $whiteback $bold
	                	echo "No Lyrics Found - Search Manually"
	                	echo $reset $black $redback
	                	read -e -p "Artist:$reset$yellow" -i "$_ARTIST" _ARTIST
	                	echo $reset $black $redback
	                	read -e -p "Title:$reset$yellow" -i "$_TITLE" _TITLE
	                	_ARTIST=$(echo "$_ARTIST" | perl -ne 'print lc')
				_TITLE=$(echo "$_TITLE" | perl -ne 'print lc')
				echo $reset $cyan
	                	_URL="${_TPL//"<artist>"/$_ARTIST}"
	                	_URL="${_URL//"<title>"/$_TITLE}"
		        	makeitpersonal
				minsize
			fi
			if [ ! -s "$_LYRFILE" ] ; then
				songmeanings
				minsize
			fi
			if [ ! -s "$_LYRFILE" ] ; then
	        	        lyricswiki
				minsize
	        	fi
			if [ ! -s "$_LYRFILE" ] ; then
                                songlyrics
                                minsize
                        fi
                        if [ ! -s "$_LYRFILE" ] ; then
                                songtexte
                                minsize
                        fi
			if [ ! -s "$_LYRFILE" ] ; then
                                darklyrics
                                minsize
                        fi

		fi
	fi
#graphical web search
	if [ ! -s "$_LYRFILE" ] ; then
		echo $yellow
		read -p "Launch Graphical Search? " -n 1 -r
		echo $reset
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
		minsize
	fi

	if [ -s "$_LYRFILE" ] ;then
		chmod 777 "$_LYRFILE" >/dev/null 2>&1
	        cat "$_LYRFILE"
		translatelyric
	else
	        echo "$_ARTIST - $_TITLE" >> /var/log/lyrics.log
	        sort -u /var/log/lyrics.log -o /var/log/lyrics.log
	fi
	echo ""
fi
echo $reset
