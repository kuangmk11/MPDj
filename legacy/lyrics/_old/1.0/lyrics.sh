#!/bin/bash
source /etc/myscripts/colors.sh
source /etc/myscripts/mpd/lyrics/variables
#_ARTIST="$(mpc -f '%artist%' | head -n 1 | sed 's|\/|_|' | perl -ne 'print lc')"
#_TITLE="$(mpc -f '%title%' | head -n 1 | sed 's|\/|_|' | sed -r 's|\s*\(.+\)||g' | sed -r 's|\s*\[.+\]||g' | perl -ne 'print lc')"
##_TITLE="$(mpc -f '%title%' | head -n 1 | sed 's|\/|_|' | perl -ne 'print lc')"
##echo "$_TITLE"
##exit
#_PATH_ARTIST=${_ARTIST//[:+=.,]}
#_PATH_TITLE=${_TITLE//[:+=.,]}
#_2ARTIST=$(echo "$_ARTIST" | sed -r 's/Christian Death.+/Christian Death/')
#_LYRPATH="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST"
#_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.txt"
#lrc_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.lrc"
#_file=/tmp/lyrics.tmp
#_TPL='http://makeitpersonal.co/lyrics?artist=<artist>&title=<title>'
#_SRY="Sorry, We don't have lyrics for this song yet."
#_URL="${_TPL//"<artist>"/$_2ARTIST}"
#_URL="${_URL//"<title>"/$_TITLE}"

clear

if [[ $1 = -d ]]
then
rm "$_LYRFILE"
nano "$_LYRFILE"
exit
fi

if [[ $1 = -e ]]
then
nano "$_LYRFILE"
exit
fi

if [[ $1 = -m ]]
then
        echo $reset $black $redback
        read -e -p "Artist:$reset$yellow" _2ARTIST
        echo $reset $black $redback
        read -e -p "Title:$reset$yellow" _TITLE
        echo $reset
	_2ARTIST=$(echo "$_2ARTIST" | perl -ne 'print lc')
	_TITLE=$(echo "$_TITLE" | perl -ne 'print lc')
	_PATH_ARTIST=${_2ARTIST//[:+=.,]}
	_PATH_TITLE=${_TITLE//[:+=.,]}
	_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.txt"
	lrc_LYRFILE="/storage/dd1/mp3/_lyrics/$_PATH_ARTIST/$_PATH_ARTIST - $_PATH_TITLE.lrc"
fi


echo $red
echo "$_2ARTIST"
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
	        _LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
	        if [ "$_LYRICS" != "$_SRY" ]; then
	                mkdir "$_LYRPATH" >/dev/null 2>&1
	                echo "$_LYRICS" > "$_LYRFILE"
	                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
	         else
	                ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_2ARTIST" "$_TITLE" 2> /dev/null >> "$_file"
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
	                        _3ARTIST=$(echo "$_3ARTIST" | perl -ne 'print lc')
				_2TITLE=$(echo "$_2TITLE" | perl -ne 'print lc')
				echo $reset $cyan
	                        _URL="${_TPL//"<artist>"/$_3ARTIST}"
	                        _URL="${_URL//"<title>"/$_2TITLE}"
	                        _LYRICS=$(wget -qO- "$_URL" | sed '/./,$!d')
	                        if [ "$_LYRICS" != "$_SRY" ]; then
	                                mkdir "$_LYRPATH" >/dev/null 2>&1
	                                echo "$_LYRICS" > "$_LYRFILE"
	                                #eyeD3 --lyrics=eng:Lyrics:"$_LYRICS" "$_FILE" 1>/dev/null
	                        else
	                                ruby /etc/myscripts/mpd/lyrics/.support/20-lyricwiki.rb "$_3ARTIST" "$_2TITLE" 2> /dev/null >> "$_file"
	                        fi
	                fi
	        fi
	fi
	if [ -s "$_LYRFILE" ] ; then
	        touch "$_LYRFILE"
	elif [ -s "$_file" ] ; then
	        mkdir "$_LYRPATH" >> /dev/null 2>&1
	        sed -i "s/&#8217;/'/" "$_file"
	        sed -i "s#<b>##" "$_file"
	        sed -i "s#<i>##" "$_file"
	        sed -i "s#</b>##" "$_file"
	        sed -i "s#</i>##" "$_file"
	        sed -i "s|script>|'$'\n|gi" "$_file"
	        tail -n +2 "$_file" > "$_LYRFILE"
	        # do something as file has data
	else
	        clear
	        echo "$_LYRFILE"
	        mkdir "$_LYRPATH" >> /dev/null 2>&1
	        nano "$_LYRFILE"
	        # do something as file is empty
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
	        cat "$_LYRFILE"
	else
	        echo "$_2ARTIST - $_TITLE" >> /var/log/lyrics.log
	        sort -u /var/log/lyrics.log -o /var/log/lyrics.log
	fi
	rm "$_file" > /dev/null 2>&1
	echo ""
fi
echo $reset
