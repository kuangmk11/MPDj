#!/usr/bin/env python

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# lastfmpdqc (last.fm mpd queuing client)
# version 0.2
# october 11, 2007
# http://endymion.beevomit.org/lastfmpdqc
#
# select random track from mpd's 'current' playlist - add tracks by
# last.fm similar artists from library to playlist
#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os, string, urllib, time, sys, random
import os.path
import audioscrobbler
import mpdclient2
import getopt

# how many songs to add at once
limit = 5

# interval between polling (in seconds)
# set to 0 for current song length
interval = 0 

# set this to where your music files are (for m3u output if its not in the m3u's mpd generates)
music_directory="/var/lib/mpd/music"

# show a menu or not
interactive = False

# whether to start playing and continue fetching suggested tracks if playlist is empty
play_on_empty = False

# track from last check
old_track = {}
old_track['artist'] = ''
old_track['title'] = ''

def connection():
	m = mpdclient2.connect()
	if not m:
		print "Couldn't connect to mpd!"
		exit()
	return m


def fetch_similar(tag):
	global interval
	global old_track
	
	m = connection()
	
	mpd_current_playlist = m.playlistinfo()
	
	mpd_track = m.currentsong()
	
	if not mpd_track:
		mpd_track = random.choice(mpd_current_playlist)
	
	if mpd_track['artist'] == old_track['artist']:
		# the song hasn't changed, or not enough
		return
	else:
		old_track = mpd_track
		
	
	fill_song(mpd_track)
	
	if interval == 0:
		interval = mpd_track.time

	mpd_target_tag = mpd_track[tag]

	safeprint("Fetching suggested songs for %s" % mpd_target_tag)

	cloud = audioscrobbler.AudioScrobblerQuery(artist = urllib.quote_plus(mpd_target_tag))

	similar_cloud = cloud.similar()
	similar_artists = []
	similar_songs = []

	# look for songs in library by artists returned 
	for artist in similar_cloud:
		this_artist = artist.name
		
		try:
			similar_songs += (m.search('artist',this_artist))
		except:
			pass
		
	add(m,similar_songs)
	
def add(connection, song_list):
	#add however many we're supposed to from the list
	count = 0
	
	similar_songs = song_list
	
	if limit > len(similar_songs):
		safe_limit = len(similar_songs)
	else:
		safe_limit = limit

	random_selection = []
	while count < safe_limit:
		random_file = random.choice(similar_songs)
			
		# check for dupes - don't add if the song is already in the playlist
		#if random_file and random_file not in mpd_current_playlist:
		fill_song(random_file)
		random_selection.append(random_file)
			
		count +=1
	
	
	random_selection = unique(random_selection) #this should check entire playlist
		
	if not interactive:
		mpd_out(connection,random_selection)
	else:
		#show_menu(connection, random_selection)
		show_menu(random_selection)

def show_menu(song_list):
	menu_index = 1

	print "==========================================================="
	for item in song_list:
		fill_song(item)
		
		#build menu
		
		print str(menu_index) + ") " + item.artist + " - " + item.title
		menu_index += 1
		
	print "==========================================================="
	answer = int(raw_input("Choose: "))
	print "==========================================================="
	mpd_out(connection, [song_list[answer-1]])

# song vs. song_list ???
def mpd_out(connection, song_list):
	for song in song_list:
		connection.add(song['file'])
		safeprint("Added " + song.artist + " - " + song.title)

def m3u_out(file,song_list):
# TODO: finish this!
	for song in song_list:
		print song.file
		
# handle missing tags
def fill_song(song):
    if not song.has_key('artist'):
     	song['artist'] = ''
    if not song.has_key('title'):
        song['title'] = ''
    if not song.has_key('album'):
        song['album'] = ''
    if not song.has_key('track'):
        song['track'] = ''

# Safe printing: can print any unicode string
def safeprint(msg):
    if msg[-1] == '\n':
        msg = msg[:-1]
    print msg

def unique(seq, keepstr=True):
  t = type(seq)
  if t in (str, unicode):
    t = (list, ''.join)[bool(keepstr)]
  seen = []
  return t(c for c in seq if not (c in seen or seen.append(c)))


def is_playing(connection):
	m = connection
	return ('play' == m.status()['state'])

def current_playlist_length(connection):
	current_playlist = connection.playlistinfo()
	pl_time = 0.0
	
	for each_track in current_playlist:
		pl_time = pl_time + float(each_track.time)
	
	return pl_time

def add_random_track(connection):
	m = connection
	random_track = [random.choice(m.listallinfo())]
	mpd_out(m,random_track)

def is_empty_playlist(connection):
	m = connection
	plength = m.status()['playlistlength']
	return (int(plength) == 0)

# "main"
#count = 0
#while count < 1:
while 1:
	try:
		# check for empty playlist
		#count = count + 1
		if is_empty_playlist(connection()):
			print("Playlist empty.")
			add_random_track(connection())
			
			if play_on_empty:
				connection().play()
				
		# check if mpd is playing. don't add if not
		if is_playing(connection()):
			fetch_similar('artist')
			
		time.sleep(float(interval))

	except EOFError:
		pass
	
