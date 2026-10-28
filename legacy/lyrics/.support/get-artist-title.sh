#!/bin/bash
_ARTIST="$(mpc -f '%artist%' | head -n 1)"
_ALBUM="$(mpc -f '%title%' | head -n 1)"

echo "$_ALBUM"
