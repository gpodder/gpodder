#!/bin/bash

usage="Usage: $0 /path/to/gpodder-x.y.z_w.deps.zip"

if [ -z "$1" ] ; then
	echo "$usage"
	exit -1
elif [ ! -f "$1" ] ; then
	echo "$usage"
	echo
	echo "E: deps not found: $1 doesn't exist"
	echo "   get them from https://github.com/gpodder/gpodder-osx-bundle/releases"
	exit -1
else
	deps="$1"
	shift
fi

set -e
set -x

me=$(readlink "$0" || echo $0)
mydir=$(cd $(dirname "$me"); pwd -P)
checkout=$(dirname $(dirname "$mydir"))

# directory where the generated app and zip will end in
workspace="$mydir/_build"

app="$workspace"/gPodder.app

contents="$app"/Contents
resources="$contents"/Resources
macos="$app"/Contents/MacOS
run_python="$macos"/run-python
run_pip="$macos"/run-pip

mkdir -p "$workspace"
rm -rf "$app" "$workspace/gPodder.contents"
cd "$workspace"
unzip "$deps"

if [ ! -e "$app/" ]; then
	echo "E: unzipping deps didn't generate $app"
	exit -1
fi

# launcher scripts
mv "$macos"/{gPodder,gpodder}
CMDS="gpo gpodder-migrate2tres run-python run-pip"
for cmd in ${CMDS}; do
    cp -a "$macos"/{gpodder,$cmd}
    if [ -e "$workspace/$cmd" ]; then
        unlink "$workspace/$cmd"
    fi
    ln -s gPodder.app/Contents/MacOS/$cmd "$workspace/"
done

# install gPodder hard dependencies
$run_pip install setuptools wheel
$run_pip install podcastparser==0.6.6 mygpoclient==1.8 requests[socks]==2.25.1

# install extension dependencies; no explicit version for youtube_dl
$run_pip install podcastparser==0.6.6 mygpoclient==1.8 mutagen==1.45.1 html5lib==1.1 youtube_dl

cd "$checkout"
touch share/applications/gpodder{,-url-handler}.desktop
export GPODDER_INSTALL_UIS="cli gtk"

# compile translations
for po in po/*; do
	lang=$(basename ${po%.po})
	msgdir=$resources/share/locale/$lang/LC_MESSAGES
	mkdir -p "$msgdir"
	$macos/msgfmt $po -o $msgdir/gpodder.mo
done

# copy fake dbus
cp -r tools/fake-dbus-module/dbus $resources/lib/python3.8/site-packages/dbus

# install
"$run_python" setup.py install --root="$resources/" --prefix=. --optimize=0

find "$app" -name '*.pyc' -delete
find "$app" -name '*.pyo' -delete
rm -Rf "$resources"/share/applications
rm -Rf "$resources"/share/dbus-1

# Command-XX shortcuts in gPodder menus
/usr/bin/xsltproc -o menus.ui.tmp "$checkout"/tools/mac-osx/adjust-modifiers.xsl "$resources"/share/gpodder/ui/gtk/menus.ui
mv menus.ui.tmp "$resources"/share/gpodder/ui/gtk/menus.ui

# Set the version and copyright automatically
version=$(perl -ne "/__version__\\s*=\\s*'(.+)'/ && print \$1" "$checkout"/src/gpodder/__init__.py)
copyright=$(perl -ne "/__copyright__\\s*=\\s*'(.+)'/ && print \$1" "$checkout"/src/gpodder/__init__.py)
sed "s/__VERSION__/$version/g" "$checkout/tools/mac-osx/Info.plist" | sed "s/__COPYRIGHT__/$copyright/g" > "$contents"/Info.plist

# Copy the latest icons
cp "$checkout"/tools/mac-osx/icon.icns "$resources"/gPodder.icns

# release the thing
"$mydir"/release.sh "$app" "$version"
