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
        git \
        gettext \
        base-devel \
        "${MINGW_PACKAGE_PREFIX}"-gdk-pixbuf2 \
        "${MINGW_PACKAGE_PREFIX}"-librsvg \
        "${MINGW_PACKAGE_PREFIX}"-gtk3 \
        "${MINGW_PACKAGE_PREFIX}"-toolchain

    pacman --noconfirm -S --needed \
        "${MINGW_PACKAGE_PREFIX}"-python \
        "${MINGW_PACKAGE_PREFIX}"-python-gobject \
        "${MINGW_PACKAGE_PREFIX}"-python-cairo \
        "${MINGW_PACKAGE_PREFIX}"-python-pip \
        "${MINGW_PACKAGE_PREFIX}"-python-six \
        "${MINGW_PACKAGE_PREFIX}"-python-webencodings \
        "${MINGW_PACKAGE_PREFIX}"-python-html5lib \
        "${MINGW_PACKAGE_PREFIX}"-python-requests \
        "${MINGW_PACKAGE_PREFIX}"-python-pillow \
        "${MINGW_PACKAGE_PREFIX}"-python-filelock \
        "${MINGW_PACKAGE_PREFIX}"-python-pywin32-ctypes \

    CFLAGS="-I${MINGW_PREFIX}/include -L${MINGW_PREFIX}/lib" pip3 install --user podcastparser mygpoclient
}

main;
