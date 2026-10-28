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

class MPD
{
    private $conn = false;

    public function __construct()
    {
        if (!$this->conn)
        {
           /* $this->conn = @fsockopen(MPD_HOST, MPD_PORT, &$errno, &$errstr, 5);*/
            $this->conn = @fsockopen(MPD_HOST, MPD_PORT, $errno, $errstr, 5);

            if (!$this->conn)
                throw new Exception("Unable to connect to MPD server: ".$errno." - ".$errstr);

            fgets($this->conn, 1024);
            //stream_set_blocking($this->conn, true);
        }
    }

    static private function compareText($a, $b)
    {
        $a = strtolower(trim($a));
        $b = strtolower(trim($b));
        $i = levenshtein($a, $b);
        $p = 100 - round(100 * ($i / strlen($a)));
        return $p;
    }

    public function __destruct()
    {
        $this->sendCommand('close');
        fclose($this->conn);
    }

    private function sendCommand($command)
    {
        fwrite($this->conn, $command . "\n");
    }

    private function fetchDatas()
    {
        if (feof($this->conn))
            return false;

        $line = fgets($this->conn, 1024);

        if (empty($line) || trim($line) == 'OK' || trim($line) == 'ACK')
            return false;

        $line = utf8_decode($line);

        return $line;
    }

    private function resetPointer()
    {
        while ($this->fetchDatas())
        {
        }
    }

    public function searchTrack($title, $artist)
    {
        $this->sendCommand('search title "'.addslashes($title).'"');

        $current_file = '';
        $current_datas = '';

        while ($line = $this->fetchDatas())
        {
            if (preg_match('!^file: (.*)!i', $line, $match))
            {
                $current_file = $match[1];
                $current_datas = $line;
            }
            else
            {
                $current_datas .= $line;
            }

            if ($current_file
                && preg_match('!Artist: (.*)!i', $current_datas, $a_match))
            {
                $a_match[1] = utf8_encode($a_match[1]);

                if ($a_match[1] == $artist || self::compareText($artist, $a_match[1]) > 90)
                {
                    $this->resetPointer();
                    return $current_file;
                }
            }
        }

        // Only one result, trying to figure out if it's just a typo
        if ($current_file && !empty($a_match) && self::compareText($artist, $a_match[1]) > 70)
        {
            return $current_file;
        }

        return false;
    }

    public function buildListFromArray($array)
    {
        $out = '';

        foreach ($array as $id=>$item)
        {
            if ($file = $this->searchTrack($item['title'], $item['artist']))
                $out .= $file . "\n";
        }

        return $out;
    }

    public function listAll()
    {
        if (!isset($this->listall))
        {
            $this->sendCommand('listall');
            $this->listall = true;
        }

        $line = $this->fetchDatas();

        if (!$line)
        {
            unset($this->listall);
            return false;
        }

        if (preg_match('!file: (.*)!i', $line, $match))
            return $match[1] . "\n";

        return true;
    }
}

?>
