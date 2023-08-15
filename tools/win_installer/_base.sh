#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -e
DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}"

# CONFIG START

ARCH="i686"
BUILD_VERSION="0"

# CONFIG END

MISC="${DIR}"/misc
if [ "${ARCH}" = "x86_64" ]; then
    MINGW="mingw64"
else
    MINGW="mingw32"
fi

GPO_VERSION="0.0.0"
GPO_VERSION_DESC="UNKNOWN"

function set_build_root {
    BUILD_ROOT="$1"
    REPO_CLONE="${BUILD_ROOT}"/gpodder
    MINGW_ROOT="${BUILD_ROOT}/${MINGW}"
}

if [ "$APPVEYOR" == "True" ]; then
	set_build_root "$HOME/_gpodder_build_root"
elif [ -d "/home/IEUser" ]; then
	set_build_root "/home/IEUser/_gpodder_build_root"
else
	set_build_root "${DIR}/_build_root"
fi

function build_pacman {
    pacman --root "${BUILD_ROOT}" "$@"
}

function build_pip {
    "${MINGW_ROOT}"/bin/python3.exe -m pip "$@"
}

function build_python {
    "${MINGW_ROOT}"/bin/python3.exe "$@"
}

function build_compileall {
    MSYSTEM= build_python -m compileall -b "$@"
}

function install_pre_deps {
	# install python3 here to ensure same version
    pacman -S --needed --noconfirm p7zip git dos2unix rsync \
        mingw-w64-"${ARCH}"-nsis wget libidn2 libopenssl intltool mingw-w64-"${ARCH}"-toolchain \
        mingw-w64-"${ARCH}"-python3
}

function create_root {
    mkdir -p "${BUILD_ROOT}"

    mkdir -p "${BUILD_ROOT}"/var/lib/pacman
    mkdir -p "${BUILD_ROOT}"/var/log
    mkdir -p "${BUILD_ROOT}"/tmp

    build_pacman -Syu
    build_pacman --noconfirm -S base
}

function extract_installer {
    [ -z "$1" ] && (echo "Missing arg"; exit 1)

    mkdir -p "$BUILD_ROOT"
    7z x -o"$BUILD_ROOT"/"$MINGW" "$1"
    rm -rf "$MINGW_ROOT"/'$PLUGINSDIR' "$MINGW_ROOT"/*.txt "$MINGW_ROOT"/*.nsi
}

PIP_REQUIREMENTS="\
certifi==2023.7.22
chardet==5.1.0
comtypes==1.2.0
git+https://github.com/jaraco/pywin32-ctypes.git@f27d6a0
html5lib==1.1
idna==3.4
mutagen==1.46.0
mygpoclient==1.9
podcastparser==0.6.10
PySocks==1.7.1
requests==2.31.0
urllib3==2.0.4
webencodings==0.5.1
yt-dlp
"

function install_deps {

    # We don't use the fontconfig backend, and this skips the lengthy
    # cache update step during package installation
    export MSYS2_FC_CACHE_SKIP=1

    build_pacman --noconfirm -S git mingw-w64-"${ARCH}"-gdk-pixbuf2 \
        mingw-w64-"${ARCH}"-librsvg \
        mingw-w64-"${ARCH}"-gtk3 mingw-w64-"${ARCH}"-python3 \
        mingw-w64-"${ARCH}"-python3-gobject \
        mingw-w64-"${ARCH}"-python3-cairo \
        mingw-w64-"${ARCH}"-python3-pip \
        mingw-w64-"${ARCH}"-python-six \
		mingw-w64-"${ARCH}"-make

    build_pacman -S --noconfirm mingw-w64-"${ARCH}"-python3-setuptools

    build_pip install --no-deps --no-binary ":all:" --upgrade \
        --force-reinstall $(echo "$PIP_REQUIREMENTS" | tr ["\\n"] [" "])

    # replace ca-certificates with certifi's
    build_pacman --noconfirm -Rdds mingw-w64-"${ARCH}"-ca-certificates || true
    mkdir -p ${MINGW_ROOT}/ssl
    site_packages=$(build_python -c  'import sys;print(next(c for c in sys.path if "site-packages" in c and ".local" not in c))')
    cp -v ${site_packages}/certifi/cacert.pem ${MINGW_ROOT}/ssl/cert.pem

    build_pacman --noconfirm -Rdds mingw-w64-"${ARCH}"-python3-pip || true
}

function install_gpodder {
    [ -z "$1" ] && (echo "Missing arg"; exit 1)

    rm -Rf "${REPO_CLONE}"
	if [ "$2" == "rsync" ]; then
	    # development mode when not everything is committed
	    rsync -rvt "${DIR}"/../.. "${REPO_CLONE}"
    else
        git clone "${DIR}"/../.. "${REPO_CLONE}"
    fi

    (cd "${REPO_CLONE}" && git checkout "$1") || exit 1

    (cd "${REPO_CLONE}" && PYTHON="${MINGW_ROOT}"/bin/python3.exe mingw32-make install-win)

    GPO_VERSION=$(MSYSTEM= build_python -c \
        "import gpodder; import sys; sys.stdout.write(gpodder.__version__)")
    GPO_VERSION_DESC="$GPO_VERSION"
    if [ "$1" = "master" ]
    then
        local GIT_REV=$(cd "${REPO_CLONE}" && git rev-list --count HEAD)
        local GIT_HASH=$(cd "${REPO_CLONE}" && git rev-parse --short HEAD)
        GPO_VERSION_DESC="$GPO_VERSION-rev$GIT_REV-$GIT_HASH"
    fi

    # Create launchers
    echo "python3 is $(which python3) version is $(python3 --version)"
    python3 "${MISC}"/create-launcher.py \
        "${GPO_VERSION}" "${MINGW_ROOT}"/bin

	# install fake dbus
    site_packages=$(build_python -c  'import sys;print(next(c for c in sys.path if "site-packages" in c and ".local" not in c))')
    site_packages_unix=$(echo "/$site_packages" | sed -e 's/\\/\//g' -e 's/://')
    rsync -arv --delete "${REPO_CLONE}"/tools/fake-dbus-module/dbus "${site_packages_unix}/"
	
	# install gtk3 settings for a proper font
	mkdir -p "${MINGW_ROOT}"/etc/gtk-3.0
	cp "${MISC}"/gtk3.0_settings.ini "${MINGW_ROOT}"/etc/gtk-3.0/settings.ini
	
	# install bin/gpodder bin/gpo to a separate package, to be run before gpodder/__init__.py
	gpodder_launch_dir="${site_packages_unix}"/gpodder_launch
	mkdir -p "${gpodder_launch_dir}"
	touch "${gpodder_launch_dir}"/__init__.py
	cp ${REPO_CLONE}/bin/gpo "${gpodder_launch_dir}"/gpo.py
	cp ${REPO_CLONE}/bin/gpodder "${gpodder_launch_dir}"/gpodder.py

    build_compileall -d "" -f -q "$(cygpath -w "${MINGW_ROOT}")"

    # copy gpodder.ico for notification-win32
    cp ${REPO_CLONE}/tools/win_installer/misc/gpodder.ico "${MINGW_ROOT}"/bin
}

function cleanup_before {
    # these all have svg variants
    find "${MINGW_ROOT}"/share/icons -name "*.symbolic.png" -exec rm -f {} \;

    # remove some larger ones
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/512x512"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/256x256"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/96x96"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/48x48"
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/Adwaita

    # remove some gtk demo icons
    find "${MINGW_ROOT}"/share/icons/hicolor -name "gtk3-*" -exec rm -f {} \;
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/hicolor

    # python related, before installing gpodder
    rm -Rf "${MINGW_ROOT}"/lib/python3.*/test
    rm -f "${MINGW_ROOT}"/lib/python3.*/lib-dynload/_tkinter*
    find "${MINGW_ROOT}"/lib/python3.* -type d -name "test*" \
        -prune -exec rm -rf {} \;
    find "${MINGW_ROOT}"/lib/python3.* -type d -name "*_test*" \
        -prune -exec rm -rf {} \;

    find "${MINGW_ROOT}"/bin -name "*.pyo" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "*.pyc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -type d -name "__pycache__" -prune -exec rm -rf {} \;

    build_compileall -d "" -f -q "$(cygpath -w "${MINGW_ROOT}")"
    find "${MINGW_ROOT}" -name "*.py" -exec rm -f {} \;
}

function cleanup_after {
    # delete translations we don't support
    for d in "${MINGW_ROOT}"/share/locale/*/LC_MESSAGES; do
        if [ ! -f "${d}"/gpodder.mo ]; then
            rm -Rf "${d}"
        fi
    done

    find "${MINGW_ROOT}" -regextype "posix-extended" -name "*.exe" -a ! \
        -iregex ".*/(gpodder|gpo|python)[^/]*\\.exe" \
        -exec rm -f {} \;

    rm -Rf "${MINGW_ROOT}"/libexec
    rm -Rf "${MINGW_ROOT}"/share/gtk-doc
    rm -Rf "${MINGW_ROOT}"/include
    rm -Rf "${MINGW_ROOT}"/var
    rm -Rf "${MINGW_ROOT}"/etc/fonts
    rm -Rf "${MINGW_ROOT}"/etc/pki
    rm -Rf "${MINGW_ROOT}"/share/zsh
    rm -Rf "${MINGW_ROOT}"/share/pixmaps
    rm -Rf "${MINGW_ROOT}"/share/gnome-shell
    rm -Rf "${MINGW_ROOT}"/share/dbus-1
    rm -Rf "${MINGW_ROOT}"/share/gir-1.0
    rm -Rf "${MINGW_ROOT}"/share/doc
    rm -Rf "${MINGW_ROOT}"/share/man
    rm -Rf "${MINGW_ROOT}"/share/info
    rm -Rf "${MINGW_ROOT}"/share/mime
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/libtool
    rm -Rf "${MINGW_ROOT}"/share/licenses
    rm -Rf "${MINGW_ROOT}"/share/appdata
    rm -Rf "${MINGW_ROOT}"/share/aclocal
    rm -Rf "${MINGW_ROOT}"/share/ffmpeg
    rm -Rf "${MINGW_ROOT}"/share/vala
    rm -Rf "${MINGW_ROOT}"/share/readline
    rm -Rf "${MINGW_ROOT}"/share/xml
    rm -Rf "${MINGW_ROOT}"/share/bash-completion
    rm -Rf "${MINGW_ROOT}"/share/common-lisp
    rm -Rf "${MINGW_ROOT}"/share/emacs
    rm -Rf "${MINGW_ROOT}"/share/gdb
    rm -Rf "${MINGW_ROOT}"/share/libcaca
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/gst-plugins-base
    rm -Rf "${MINGW_ROOT}"/share/gst-plugins-bad
    rm -Rf "${MINGW_ROOT}"/share/libgpg-error
    rm -Rf "${MINGW_ROOT}"/share/p11-kit
    rm -Rf "${MINGW_ROOT}"/share/pki
    rm -Rf "${MINGW_ROOT}"/share/thumbnailers
    rm -Rf "${MINGW_ROOT}"/share/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/share/nghttp2
    rm -Rf "${MINGW_ROOT}"/share/themes
    rm -Rf "${MINGW_ROOT}"/share/fontconfig
    rm -Rf "${MINGW_ROOT}"/share/gettext-*
    rm -Rf "${MINGW_ROOT}"/share/gstreamer-1.0
    rm -Rf "${MINGW_ROOT}"/share/installed-tests

    find "${MINGW_ROOT}"/share/glib-2.0 -type f ! \
        -name "*.compiled" -exec rm -f {} \;

    # unused configuration example
    rm -Rf "${MINGW_ROOT}"/ssl/openssl.cnf

    rm -Rf "${MINGW_ROOT}"/lib/cmake
    rm -Rf "${MINGW_ROOT}"/lib/gettext
    rm -Rf "${MINGW_ROOT}"/lib/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/lib/mpg123
    rm -Rf "${MINGW_ROOT}"/lib/p11-kit
    rm -Rf "${MINGW_ROOT}"/lib/pkcs11
    rm -Rf "${MINGW_ROOT}"/lib/ruby
    rm -Rf "${MINGW_ROOT}"/lib/engines

    # remove all tcl/tk libs
    rm -Rf "${MINGW_ROOT}"/lib/dde*
    rm -Rf "${MINGW_ROOT}"/lib/itcl*
    rm -Rf "${MINGW_ROOT}"/lib/reg*
    rm -Rf "${MINGW_ROOT}"/lib/tcl*
    rm -Rf "${MINGW_ROOT}"/lib/tdbc*
    rm -Rf "${MINGW_ROOT}"/lib/tk*

    # remove terminfo database (not used, even by gpo)
    rm -Rf "${MINGW_ROOT}"/lib/terminfo
    rm -Rf "${MINGW_ROOT}"/share/terminfo

    rm -f "${MINGW_ROOT}"/bin/libharfbuzz-icu-0.dll
    rm -Rf "${MINGW_ROOT}"/lib/python2.*

    find "${MINGW_ROOT}" -name "*.a" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.whl" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.h" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.la" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.sh" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.jar" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.def" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmd" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmake" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.desktop" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.manifest" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pyo" -exec rm -f {} \;

    find "${MINGW_ROOT}"/bin -name "*-config" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "easy_install*" -exec rm -f {} \;
    find "${MINGW_ROOT}" -regex ".*/bin/[^.]+" -exec rm -f {} \;
    find "${MINGW_ROOT}" -regex ".*/bin/[^.]+\\.[0-9]+" -exec rm -f {} \;

    find "${MINGW_ROOT}" -name "gtk30-properties.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "gettext-tools.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "libexif-12.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "xz.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "libgpg-error.mo" -exec rm -rf {} \;

    find "${MINGW_ROOT}" -name "old_root.pem" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "weak.pem" -exec rm -rf {} \;

    find "${MINGW_ROOT}"/bin -name "*.pyo" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "*.pyc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -type d -name "__pycache__" -prune -exec rm -rf {} \;

    build_python "${MISC}/depcheck.py" --delete

    find "${MINGW_ROOT}" -type d -empty -delete
}

function dump_packages {
	DUMPFILE="${MINGW_ROOT}/contents.txt"
	pkg=""
	rm -f "$DUMPFILE"
	(
		unset PKGVERSIONS
		declare -A PKGVERSIONS
		while read pkg version; do
			PKGVERSIONS[$pkg]="$version"
		done < <(build_pacman -Q)
		# REGFILES is a hash of file -> package name to check for unregistered files in the end
		unset REGFILES
		declare -A REGFILES
		echo "msys2 packages:"
		# first handle all files registered with pacman
		while read _pkg file; do
			realfile=""
			if [[ "$file" == "${MINGW_ROOT}"* ]]; then
				if [ -f "$file" ]; then
					realfile="$file"
				elif [[ "$file" == *".py" ]] && [ -f "${file}c" ]; then
					realfile="${file}c"
				fi
			fi
			if [ -n "$realfile" ]; then
				if [ "$_pkg" != "$pkg" ]; then
					pkg="$_pkg"
					echo "$pkg ${PKGVERSIONS[$pkg]}"
				fi
				echo "    ${realfile#${MINGW_ROOT}}"
				REGFILES["$realfile"]="$pkg"
			fi
		done < <(build_pacman -Ql)
		echo "==================="
		# then handle all python packages (with an installed-files.txt)
		echo "Python packages:"
		for p in ${PIP_REQUIREMENTS}; do
			pkg=${p%==*}
			version=${p#*==}
			echo "$pkg $version"
			# pywin32-ctypes doesn't provide an egg-info/installed-files.txt
			if [ "$pkg" == "pywin32-ctypes" ]; then
				while read file; do
					if [ ! ${REGFILES[$file]+_} ]; then
						echo "    $file"
						REGFILES["$file"]="$pkg"
					fi
				done < <(find "${MINGW_ROOT}" -type f -a \( -path '*/site-packages/pywin32_ctypes*' -o -path '*/site-packages/win32ctypes/*' \))
			elif [ "$pkg" == "certifi" ]; then
				while read file; do
					if [ ! ${REGFILES[$file]+_} ]; then
						echo "    $file"
						REGFILES["$file"]="$pkg"
					fi
				done < <(find "${MINGW_ROOT}/ssl" -type f -path '*/ssl/cert.pem')
			else
				# other python deps provide an installed-files.txt, so simply go through them
				egg="${MINGW_ROOT}/lib/python3.6/site-packages/${pkg}-${version}-py3.6.egg-info"
				if [ -f "$egg/installed-files.txt" ]; then
					while read file; do
						realfile=""
						tryfile="$egg/$file"
						if [ -f "$tryfile" ]; then
							realfile=$(realpath "$tryfile")
						# we precompiled all python modules
						elif [[ "$tryfile" == *.py ]] && [ -f "${tryfile}c" ]; then
							realfile=$(realpath "${tryfile}c")
						fi
						# this file (or compiled module) belongs to this python package
						if [ -n "$realfile" ]; then
							echo "    $realfile"
							REGFILES["$realfile"]="$pkg"
						fi
					# installed-files.txt is not listed in itself, so add it manually
					done < <(echo installed-files.txt; tr -d '\r' < "$egg/installed-files.txt")
				fi
			fi
		done
		echo "==================="
		echo gPodder
		# every file with gpodder in the path belongs to us!
		while read relfile; do
			file="${MINGW_ROOT}/${relfile#./}"
			if [ ! ${REGFILES[$file]+_} ]; then
				echo "    $file"
				REGFILES["$file"]="gpodder"
			fi
		done < <(cd "${MINGW_ROOT}" && find . -type f -a \( -path '*gpodder*' -o -path '*/site-packages/dbus/*' -o -name gpo.exe \))
		echo "==================="
		echo "Unregistered files:"
		# a few generated files
		while read file; do
		if [ ! ${REGFILES[$file]+_} ]; then
			echo "    $file"
		fi
		done < <(find "${MINGW_ROOT}" -type f)
	) > "$DUMPFILE"
    unix2dos "${DUMPFILE}"
    cp "${DUMPFILE}" "$DIR/gpodder-$GPO_VERSION_DESC-contents.txt"
}

function build_installer {
    BUILDPY=$(echo "${MINGW_ROOT}"/lib/python3.*/site-packages/gpodder)/build_info.py
    cp "${REPO_CLONE}"/src/gpodder/build_info.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd "$REPO_CLONE" && echo "BUILD_INFO = u\"$(cd "${REPO_CLONE}" && git rev-parse --short HEAD)\"" >> "$BUILDPY")
    (cd $(dirname "$BUILDPY") && build_compileall -d "" -q -f -l .)
    rm -f "$BUILDPY"

    cp "${MISC}"/gpodder.ico "${BUILD_ROOT}"
    (cd "$BUILD_ROOT" && makensis -V3 -NOCD -DVERSION="$GPO_VERSION_DESC" "${MISC}"/win_installer.nsi)

    mv "$BUILD_ROOT/gpodder-LATEST.exe" "$DIR/gpodder-$GPO_VERSION_DESC-installer.exe"
}

function build_portable_installer {
    BUILDPY=$(echo "${MINGW_ROOT}"/lib/python3.*/site-packages/gpodder)/build_info.py
    cp "${REPO_CLONE}"/src/gpodder/build_info.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows-portable"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd "$REPO_CLONE" && echo "BUILD_INFO = u\"$(cd "${REPO_CLONE}" && git rev-parse --short HEAD)\"" >> "$BUILDPY")
    (cd $(dirname "$BUILDPY") && build_compileall -d "" -q -f -l .)
    rm -f "$BUILDPY"

    local PORTABLE="$DIR/gpodder-${GPO_VERSION_DESC}-portable"

    rm -rf "$PORTABLE"
    mkdir "$PORTABLE"
    cp "$MISC"/gpodder.lnk "$PORTABLE"
    cp "$MISC"/gpo.lnk "$PORTABLE"
    cp "$MISC"/README-PORTABLE.txt "$PORTABLE"/README.txt
    unix2dos "$PORTABLE"/README.txt
    mkdir "$PORTABLE"/config
    cp -RT "${MINGW_ROOT}" "$PORTABLE"/data

    rm -Rf 7zout 7z2201.exe
    7z a payload.7z "$PORTABLE"
    wget -P "$DIR" -c http://www.7-zip.org/a/7z2201.exe
    7z x -o7zout 7z2201.exe
    cat 7zout/7z.sfx payload.7z > "$PORTABLE".exe
    rm -Rf 7zout 7z2201.exe payload.7z "$PORTABLE"
}
