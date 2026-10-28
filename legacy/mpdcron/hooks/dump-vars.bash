#!/bin/bash
MPD_SONG_URI_SAN=${MPD_SONG_URI//;/%3b}
MPD_SONG_FULLPATH=$(dirname /storage/dd1/mp3/"${MPD_SONG_URI_SAN}")
MPD_ARTIST_FULLPATH=$(dirname "$MPD_SONG_FULLPATH")
MPD_SONG_PATH=$(echo "${MPD_SONG_FULLPATH}" | sed 's#/storage/dd1/mp3/##g')
MPD_ARTIST_PATH=$(echo "${MPD_ARTIST_FULLPATH}" | sed 's#/storage/dd1/mp3/##g')
MPD_SONG_WINPATH=$(echo "${MPD_SONG_WINPATH}" | sed 's#/storage/dd1/mp3/##g' | sed -e 's#/#\\#g')
MPD_SONG_FILE=$(basename /storage/dd1/mp3/"${MPD_SONG_URI_SAN}")
OUTPUT_BASEMENT=$(mpc outputs | head -n 1 | tail -n 1 | sed 's/Output 1 (Basement (Front Outputs)) is //;s/d$//')
#OUTPUT_KITCHEN=$(mpc outputs | head -n 2 | tail -n 1 | sed 's/Output 2 (Kitchen (Rear Outputs)) is //;s/d$//')
OUTPUT_STREAM=$(mpc outputs | head -n 3 | tail -n 1 | sed 's/Output 3 (Gargoyle2 HTTP Stream) is //;s/d$//')
_ARTIST=$(echo "$MPD_SONG_TAG_ARTIST" | perl -ne 'print lc')
_ARTIST=${_ARTIST//&/and}
PATH_ARTIST=${_ARTIST//[\'\"\?\:+=.,]}


if [ "$OUTPUT_BASEMENT" = "enable" ]
then
	OUTPUT_BASEMENT=disable
else
	OUTPUT_BASEMENT=enable
fi

if [ "OUTPUT_STREAM"  = "enable" ]
then
        OUTPUT_STREAM=disable
else
        OUTPUT_STREAM=enable
fi
#if [ "OUTPUT_KITCHEN"  = "enable" ]
#then
#        OUTPUT_KITCHEN=disable
#else
#        OUTPUT_KITCHEN=enable
#fi


echo "<?php "
echo ""
echo "\$PATH_ARTIST = ###$PATH_ARTIST###;" 							#URI of the song
echo "\$MPD_SONG_URI_SAN = ###$MPD_SONG_URI_SAN###;" 							#URI of the song
echo "\$MPD_SONG_URI = ###$MPD_SONG_URI###;" 							#URI of the song
echo "\$MPD_SONG_PATH = ###$MPD_SONG_PATH###;" 							#song path mpd reletive
echo "\$MPD_SONG_FULLPATH = ###$MPD_SONG_FULLPATH###;" 						#full path
echo "\$MPD_ARTIST_FULLPATH = ###$MPD_ARTIST_FULLPATH###;" 						#full path
echo "\$MPD_ARTIST_PATH = ###$MPD_ARTIST_PATH###;" 						#full path
#echo "\$MPD_SONG_WINPATH = ###$MPD_SONG_WINPATH###;" 						#win path
echo "\$MPD_SONG_FILE = ###$MPD_SONG_FILE###;" 							#file name
echo "\$MPD_SONG_LAST_MODIFIED = ###$MPD_SONG_LAST_MODIFIED###;"  				#Time of last modification (format = "%Y-%m-%d %H-%M-%S %Z")
echo "\$MPD_SONG_DURATION = ###$MPD_SONG_DURATION###;"  					#Duration of the song in seconds
echo "\$MPD_SONG_POS = ###$MPD_SONG_POS###;" 							#Position of the song in the queue
echo "\$MPD_SONG_ID = ###$MPD_SONG_ID###;" 							#Song ID
echo "\$MPD_SONG_TAG_ARTIST = ###$MPD_SONG_TAG_ARTIST###;" | sed 's|&|and|g' | sed 's|:||'	#Artist tag
echo "\$MPD_SONG_TAG_ALBUM = ###$MPD_SONG_TAG_ALBUM###;" | sed 's|&|and|g' 			#Album tag
echo "\$MPD_SONG_TAG_ALBUM_ARTIST = ###$MPD_SONG_TAG_ALBUM_ARTIST###;"  			#Album artist tag
echo "\$MPD_SONG_TAG_TITLE = ###$MPD_SONG_TAG_TITLE###;" | sed 's|&|and|g'			#Title tag
echo "\$MPD_SONG_TAG_TRACK = ###$MPD_SONG_TAG_TRACK###;"					#Track tag
#echo "\$MPD_SONG_TAG_NAME = ###$MPD_SONG_TAG_NAME###;"						#Name tag
echo "\$MPD_SONG_TAG_GENRE = ###$MPD_SONG_TAG_GENRE###;" 					#Genre tag
echo "\$MPD_SONG_TAG_DATE = ###$MPD_SONG_TAG_DATE###;" 						#Date tag
#echo "\$MPD_SONG_TAG_COMPOSER = ###$MPD_SONG_TAG_COMPOSER###;"  				#Composer tag
#echo "\$MPD_SONG_TAG_COMMENT = ###$MPD_SONG_TAG_COMMENT###;" 					#Comment tag
#echo "\$MPD_SONG_TAG_DISC = ###$MPD_SONG_TAG_DISC###;" 						#Disc tag
#echo "\$MPD_SONG_TAG_MUSICBRAINZ_ARTISTID = ###$MPD_SONG_TAG_MUSICBRAINZ_ARTISTID###;"  	#Musicbrainz artist ID
#echo "\$MPD_SONG_TAG_MUSICBRAINZ_ALBUMID = ###$MPD_SONG_TAG_MUSICBRAINZ_ALBUMID###;" 		#Musicbrainz album ID
#echo "\$MPD_SONG_TAG_MUSICBRAINZ_ALBUMARTISTID = ###$MPD_SONG_TAG_MUSICBRAINZ_ALBUMARTISTID###;"#Musicbrainz album artist ID
#echo "\$MPD_SONG_TAG_MUSICBRAINZ_TRACKID = ###$MPD_SONG_TAG_MUSICBRAINZ_TRACKID###;" 		#Musicbrainz track ID stats
#echo "\$MPD_DATABASE_UPDATE_TIME = ###$MPD_DATABASE_UPDATE_TIME###;" 				#Date specifying last update time (format = "%Y-%m-%d %H-%M-%S %Z")
#echo "\$MPD_DATABASE_ARTISTS = ###$MPD_DATABASE_ARTISTS###;" 					#Number of artists
#echo "\$MPD_DATABASE_ALBUMS = ###$MPD_DATABASE_ALBUMS###;"					#Number of albums
#echo "\$MPD_DATABASE_SONGS = ###$MPD_DATABASE_SONGS###;"					#Number of songs
#echo "\$MPD_DATABASE_PLAY_TIME = ###$MPD_DATABASE_PLAY_TIME###;" 				#Accumulated time mpd was playing music since the process was started
#echo "\$MPD_DATABASE_UPTIME = ###$MPD_DATABASE_UPTIME###;" 					#Uptime of mpd in seconds
#echo "\$MPD_DATABASE_DB_PLAY_TIME = ###$MPD_DATABASE_DB_PLAY_TIME###;" 				#Accumulated duration of all songs
#echo "\$MPD_STATUS_VOLUME = ###$MPD_STATUS_VOLUME###;" 						#Volume
echo "\$MPD_STATUS_REPEAT = ###$MPD_STATUS_REPEAT###;"						#Repeat (boolean, 0 or 1)
echo "\$MPD_STATUS_RANDOM = ###$MPD_STATUS_RANDOM###;"						#Random (boolean, 0 or 1)
echo "\$MPD_STATUS_SINGLE = ###$MPD_STATUS_SINGLE###;" 						#Single (boolean, 0 or 1)
echo "\$MPD_STATUS_CONSUME = ###$MPD_STATUS_CONSUME###;" 					#Consume (boolean, 0 or 1)
#echo "\$MPD_STATUS_QUEUE_LENGTH = ###$MPD_STATUS_QUEUE_LENGTH###;"				#Queue/Playlist length
#echo "\$MPD_STATUS_CROSSFADE = ###$MPD_STATUS_CROSSFADE###;" 					#Crossfade in seconds
#echo "\$MPD_STATUS_SONG_POS = ###$MPD_STATUS_SONG_POS###;"					#Position of the current playing song
#echo "\$MPD_STATUS_SONG_ID = ###$MPD_STATUS_SONG_ID###;" 					#ID of the current playing song
#echo "\$MPD_STATUS_ELAPSED_TIME = ###$MPD_STATUS_ELAPSED_TIME###;"				#Elapsed time in seconds
#echo "\$MPD_STATUS_ELAPSED_MS = ###$MPD_STATUS_ELAPSED_MS###;"					#Elapsed time in milliseconds
#echo "\$MPD_STATUS_TOTAL_TIME = ###$MPD_STATUS_TOTAL_TIME###;"					#Total time in seconds
#echo "\$MPD_STATUS_KBIT_RATE = ###$MPD_STATUS_KBIT_RATE###;" 					#Current bit rate in kbps
#echo "\$MPD_STATUS_UPDATE_ID = ###$MPD_STATUS_UPDATE_ID###;" 					#ID of the update
#echo "\$MPD_STATUS_STATE = ###$MPD_STATUS_STATE###;"						#State, one of play, pause, stop or unknown
#echo "\$MPD_STATUS_AUDIO_FORMAT = ###$MPD_STATUS_AUDIO_FORMAT###;"				#Specified whether audio format is available (boolean, 0 or 1)
#echo "\$MPD_STATUS_AUDIO_FORMAT_SAMPLE_RATE = ###$MPD_STATUS_AUDIO_FORMAT_SAMPLE_RATE###;"	#Sample rate in Hz
#echo "\$MPD_STATUS_AUDIO_FORMAT_BITS = ###$MPD_STATUS_AUDIO_FORMAT_BITS###;" 			#Number of significant bits per sample
echo "\$OUTPUT_BASEMENT = ###$OUTPUT_BASEMENT###;" 						#basement output status
#echo "\$OUTPUT_KITCHEN = ###$OUTPUT_KITCHEN###;" 						#kitchen output status
echo "\$OUTPUT_STREAM = ###$OUTPUT_STREAM###;" 							#stream output status
echo ""
echo "?>"

#sed -i "s|'||g" /tmp/vars.php >> /dev/null 2>&1
#sed -i "s|###|'|g" /tmp/vars.php /dev/null 2>&1
#cat /tmp/vars.php > /var/www/admin/vars.php /dev/null 2>&1

