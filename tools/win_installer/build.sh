#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

DIR="$( cd "$( dirname "$0" )" && pwd )"
source "$DIR"/_base.sh

function main {
    local GIT_TAG=${1:-"master"}

    [[ -d "${BUILD_ROOT}" ]] && (echo "${BUILD_ROOT} already exists"; exit 1)

    # started from the wrong env -> switch
    if [ -n "$MSYSTEM" ] && [ $(echo "$MSYSTEM" | tr '[A-Z]' '[a-z]') != "$MINGW" ]; then
        echo ">>>>> MSYSTEM=${MSYSTEM} - SWITCHING TO ${MINGW} <<<<"
        "/${MINGW}.exe" "$0"
        echo ">>>>> DONE WITH ${MINGW} ?? <<<<"
        exit $?
    fi

	echo ">>>> install_pre_deps <<<<"
    install_pre_deps
	echo ">>>> create_root <<<<"
    create_root
	echo ">>>> install_deps <<<<"
    install_deps
	echo ">>>> cleanup_before <<<<"
    cleanup_before
	echo ">>>> install_gpodder <<<<"
    install_gpodder "$GIT_TAG"
	echo ">>>> cleanup_after <<<<"
    cleanup_after
	echo ">>>> dump_packages <<<<"
	dump_packages
	echo ">>>> build_installer <<<<"
    build_installer
	echo ">>>> build_portable_installer <<<<"
    build_portable_installer
}

main "$@";
