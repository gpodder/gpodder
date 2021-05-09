#!/bin/bash

set -e

usage="Usage: $0 /path/to/gPodder.app version_buildnumber"

if [ -z "$1" ] ; then
	echo "$usage"
	exit -1
elif [ ! -d "$1" ] ; then
	echo "$usage"
	echo "$1 doesn't exist or is not a directory (give me /path/to/gPodder.app)"
else
	app=$1
	shift
fi

if [ -z "$1" ] ; then
	echo "$usage"
	exit -1
else
	version="$1"
	shift
fi

d=$(dirname "$app")
appname=$(basename "$app")
zip="${appname%.app}-$version.zip"
contents="${appname%.app}.contents"

if (which md5 >& /dev/null) ; then
	MD5=md5
else
	MD5=md5sum
fi

cd "$d"
if [ -f "$zip" ] ; then
	echo "$d/$zip already exists!"
	exit -1
fi
echo "Creating $d/$zip..."
zip --symlinks -rq "$zip" "$appname" "$contents"
find . -maxdepth 1 -type l -exec zip -q --symlinks "$zip" '{}' ';'

echo "Checksumming..."
shasum -a256 "$zip" > "$zip.sha256"
"$MD5" "$zip" > "$zip.md5"

echo "Done"
