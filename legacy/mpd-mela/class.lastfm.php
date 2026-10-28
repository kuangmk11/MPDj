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

class LastFM
{
    static private $library_page = 1;
    static private $library_max_page = 2;

    static private $api_url = 'http://ws.audioscrobbler.com/2.0/?';

    const PERIOD_ALL = 'overall';
    const PERIOD_3_MONTHS = '3month';
    const PERIOD_6_MONTHS = '6month';
    const PERIOD_1_YEAR = '12month';

    static private $stream_options = array(
        'http'      =>  array(
            'method'    =>  "GET",
            'header'    =>  "User-Agent: mpd-mela/0.0.1\r\n",
            'timeout'   =>  5,
        ),
    );

    static private function makeRequest($method, $args)
    {
        $args['method'] = $method;
        $args['api_key'] = LASTFM_API_KEY;
        $args['format'] = 'json';
        $url = self::$api_url . http_build_query($args, '', '&');

        $context = stream_context_create(self::$stream_options);

        $contents = file_get_contents($url, false, $context);
        $contents = str_replace('"@attr"', '"_attr"', $contents); // Fix the json
        return json_decode($contents);
    }

    static public function getTracksLibrary()
    {
        if (self::$library_page > self::$library_max_page)
            return false;

        $api = self::makeRequest('library.getTracks', array('user' => LASTFM_USERNAME, 'page' => self::$library_page));

        if (empty($api->tracks->track))
            return false;

        self::$library_max_page = $api->tracks->_attr->totalPages;
        self::$library_page++;

        $return = array();

        foreach ($api->tracks->track as &$track)
        {
            $return[] = array(
                'artist'    =>  $track->artist->name,
                'title'     =>  $track->name,
            );
        }

        unset($api);

        if (empty($return))
            return false;

        return $return;
    }

    static public function getTopTracks($period=self::PERIOD_ALL)
    {
        $api = self::makeRequest('user.getTopTracks', array('user' => LASTFM_USERNAME, 'period' => $period));

        if (empty($api->toptracks->track))
            return false;

        $return = array();

        foreach ($api->toptracks->track as &$track)
        {
            $return[] = array(
                'artist'    =>  $track->artist->name,
                'title'     =>  $track->name,
            );
        }

        unset($api);

        if (empty($return))
            return false;

        return $return;
    }

    static public function getLovedTracks()
    {
        $api = self::makeRequest('user.getLovedTracks', array('user' => LASTFM_USERNAME));

        if (empty($api->lovedtracks->track))
            return false;

        $return = array();

        foreach ($api->lovedtracks->track as &$track)
        {
            $return[] = array(
                'artist'    =>  $track->artist->name,
                'title'     =>  $track->name,
            );
        }

        unset($api);

        if (empty($return))
            return false;

        return $return;
    }
}

?>


