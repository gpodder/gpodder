#!/bin/bash

usage="Usage: $0 /path/to/pythonbase-x.y.z_w.zip"

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
oldapp="$workspace/pythonbase.app"

contents="$app"/Contents
resources="$contents"/Resources
macos="$app"/Contents/MacOS
run_python="$macos"/run-python
run_pip="$macos"/run-pip

mkdir -p "$workspace"
rm -rf "$oldapp" "$app" "$workspace/gPodder.contents" "$workspace/pythonbase.contents"
cd "$workspace"
unzip "$deps"



if [ ! -e "$oldapp/" ]; then
	echo "E: unzipping deps didn't generate $oldapp"
	exit -1
fi

mv "$oldapp" "$app"
mv "$workspace/pythonbase.contents" "$workspace/gPodder.contents"

# launcher scripts
mv "$macos"/{pythonbase,gpodder}
CMDS="gpo gpodder-migrate2tres run-python run-pip"
for cmd in ${CMDS}; do
	if [ -e "$macos"/$cmd ]; then
		unlink "$macos"/$cmd
	fi
    cp -a "$macos"/{gpodder,$cmd}
	rm -f "$workspace/$cmd"
    ln -s $(basename $app)/Contents/MacOS/$cmd "$workspace/"
done

cp -a "$checkout"/tools/mac-osx/launcher.py "$resources"/
cp -a "$checkout"/tools/mac-osx/make_cert_pem.py "$resources"/bin

# install gPodder hard dependencies
$run_pip install setuptools==64.0.3 wheel || exit 1
$run_pip install mygpoclient==1.9 podcastparser==0.6.10 requests[socks]==2.31.0 || exit 1
# install brotli and pycryptodomex (build from source)
$run_pip debug -v
$run_pip install -v brotli || exit 1
$run_pip install -v pycryptodomex || exit 1
# install extension dependencies; no explicit version for yt-dlp
$run_pip install html5lib==1.1 mutagen==1.46.0 yt-dlp || exit 1

cd "$checkout"
touch share/applications/gpodder{,-url-handler}.desktop
cp share/dbus-1/services/org.gpodder.service{.in,}
export GPODDER_INSTALL_UIS="cli gtk"

# compile translations
for po in po/*; do
	lang=$(basename ${po%.po})
	msgdir=$resources/share/locale/$lang/LC_MESSAGES
	mkdir -p "$msgdir"
	$macos/msgfmt $po -o $msgdir/gpodder.mo
done

# copy fake dbus
cp -r tools/fake-dbus-module/dbus $resources/lib/python3.9/site-packages/dbus

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
