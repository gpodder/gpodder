#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -e

function main {
    pacman --noconfirm -Suy

    pacman --noconfirm -S --needed \
        git mingw-w64-i686-gdk-pixbuf2 \
        mingw-w64-i686-librsvg \
        mingw-w64-i686-gtk3 \
		intltool \
        base-devel mingw-w64-i686-toolchain

    pacman --noconfirm -S --needed \
        mingw-w64-i686-python3 \
        mingw-w64-i686-python3-gobject \
        mingw-w64-i686-python3-cairo \
        mingw-w64-i686-python3-pip

    pip3 install --user podcastparser mygpoclient \
						pywin32-ctypes \
						html5lib webencodings six
}

main;
