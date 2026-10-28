#!/bin/php
<?php
/*
    This file is part of MPD-Mela.

    MPD-Mela is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3 of the License.

    MPD-Mela is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MPD-Mela.  If not, see <http://www.gnu.org/licenses/>.
*/

require_once dirname(__FILE__) . '/config.php';

if (true)
{
    $db = new SQLite3(':memory:');

    $db->exec('CREATE TABLE songs (filename TEXT, path TEXT, filedate INT);');
    $db->exec('CREATE INDEX filedate ON songs (filedate);');

    echo "Listing files...\n";

    $tmp = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'mpd-mela-index';

    $cmd = 'find ' . escapeshellarg(MPD_MUSIC_DIR) . ' -type f > '.escapeshellarg($tmp);
    shell_exec($cmd);

    echo "Creating index...\n";

    $fp = fopen($tmp, 'r');

    $db->exec('BEGIN;');

    while(!feof($fp))
    {
        $line = fgets($fp, 4096);
        $name = trim($line);

        if (!preg_match('!\.('.AUDIO_FORMATS.')$!i', $name))
            continue;

        $date = filemtime($name);
        $db->exec('INSERT INTO songs (filename, path, filedate)
            VALUES (\''.$db->escapeString(basename($name)).'\', \''.$db->escapeString(dirname($name)).'\',
            \''.$date.'\');');
    }

    $db->exec('END;');

    fclose($fp);

    echo "Creating timed playlists...\n";

    $playlists = array(
        'mpdmela-all-tracks' =>  '',
        'mpdmela--y-added-last-2-years'  =>  'WHERE filedate >= '.strtotime('2 years ago'),
        'mpdmela--y-added-last-1-year'   =>  'WHERE filedate >= '.strtotime('1 year ago'),
        'mpdmela--m-added-last-6-months' =>  'WHERE filedate >= '.strtotime('6 months ago'),
        'mpdmela--m-added-last-3-months' =>  'WHERE filedate >= '.strtotime('3 months ago'),
        'mpdmela--d-added-last-30-days'  =>  'WHERE filedate >= '.strtotime('1 month ago'),
        'mpdmela--d-added-last-15-days'  =>  'WHERE filedate >= '.strtotime('15 days ago'),
        'mpdmela--d-added-last-07-days'  =>  'WHERE filedate >= '.strtotime('7 days ago'),
    );

    foreach ($playlists as $name => $query)
    {
        echo "$name\n";
        $fp = fopen(MPD_PLAYLIST_DIR . '/' . $name . '.m3u', 'w');
        $res = $db->query('SELECT * FROM songs '.$query.' ORDER BY path, filename;');

        while ($row = $res->fetchArray(SQLITE3_ASSOC))
        {
            #echo ".";
            fputs($fp, $row['path'] . DIRECTORY_SEPARATOR . $row['filename'] . "\n");
        }

        fclose($fp);
    }
}
/*
if (true)
{
    echo "free-music\n";
    $cmd = 'find ' . escapeshellarg(MPD_MUSIC_DIR) . ' -type f -iname \'license*\' ';
    $return = shell_exec($cmd);
    $return = explode("\n", $return);
    unlink(MPD_PLAYLIST_DIR . '/free-music.m3u');

    foreach ($return as $album)
    {
        $dir = dirname($album);
        if (!empty($dir))
            system('find ' . escapeshellarg($dir) . ' -type f -regextype posix-egrep -iregex \'.*\\.(' . AUDIO_FORMATS . ')$\' >> '.escapeshellarg(MPD_PLAYLIST_DIR . '/free-music.m3u'));
    }
}
*/
if (LASTFM_USERNAME != '' && true)
{
    require_once dirname(__FILE__) . '/class.lastfm.php';
    require_once dirname(__FILE__) . '/class.mpd.php';

    echo "Creating last.fm playlists...\n";

    $mpd = new MPD;
/*
    if ($tracks = LastFM::getLovedTracks())
    {
        echo "mpdmela-lastfm-loved-tracks\n";
        file_put_contents(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-loved-tracks.m3u', $mpd->buildListFromArray($tracks));
    }
*/
    if ($tracks = LastFM::getTopTracks(LastFM::PERIOD_3_MONTHS))
    {
        echo "mpdmela-lastfm-top-tracks-on-last-3-months\n";
        file_put_contents(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-top-tracks-on-last-3-months.m3u', $mpd->buildListFromArray($tracks));
    }

    if ($tracks = LastFM::getTopTracks(LastFM::PERIOD_6_MONTHS))
    {
        echo "mpdmela-lastfm-top-tracks-on-last-6-months\n";
        file_put_contents(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-top-tracks-on-last-6-months.m3u', $mpd->buildListFromArray($tracks));
    }

    if ($tracks = LastFM::getTopTracks(LastFM::PERIOD_1_YEAR))
    {
        echo "mpdmela-lastfm-top-tracks-on-last-year\n";
        file_put_contents(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-top-tracks-on-last-year.m3u', $mpd->buildListFromArray($tracks));
    }

    if ($tracks = LastFM::getTopTracks(LastFM::PERIOD_ALL))
    {
        echo "mpdmela-lastfm-top-tracks-of-all-time\n";
        file_put_contents(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-top-tracks-of-all-time.m3u', $mpd->buildListFromArray($tracks));
    }
/*
    echo "mpdmela-lastfm-favorite-tracks\n";

    $fp = fopen(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-favorite-tracks.m3u', 'w');

    while ($tracks = LastFM::getTracksLibrary())
    {
        fputs($fp, $mpd->buildListFromArray($tracks));
    }

    fclose($fp);

    echo "mpdmela-lastfm-rare-tracks\n";

    shell_exec('tac ' . escapeshellarg(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-favorite-tracks.m3u') . ' > '
        .   escapeshellarg(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-rare-tracks.m3u'));

    echo "mpdmela-lastfm-unknown-tracks\n";

    $lastfm = file(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-favorite-tracks.m3u');
    $fp = fopen(MPD_PLAYLIST_DIR . '/mpdmela-lastfm-unknown-tracks.m3u', 'w');

    while ($file = $mpd->listAll())
    {
        if ($file === true)
            continue;

        if (!in_array($file, $lastfm))
            fputs($fp, $file);
    }

    fclose($fp);
*/
}

?>

