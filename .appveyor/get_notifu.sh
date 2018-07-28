#!/bin/bash
set -e

src=notifu-src-1.6.1.zip
wget https://www.paralint.com/projects/notifu/dl/$src
checksum=$(sha256sum $src | cut -d " " -f1)
if [ "$checksum" = "0fdcd08d3e12d87af76cdaafbf1278c4fcf1baf5d6447cce1a676b8d78a4d8c3" ]; then
	echo "$src checksum OK"
else
	echo "$src checksum KO: got $checksum"
	exit 1
fi
