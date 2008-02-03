#!/bin/sh

GTK_ROOT=/c/programme/pygtk/gtk

# clean-up from last build
rm -rf build dist

# py2exe
python setup-win32.py py2exe

# copy gtk resource files
cp -r ${GTK_ROOT}/{etc,lib,share} dist/

cd dist

# remove unnecessary gtk stuff
rm -rf ./lib/gtk-2.0/2.4.0
rm -rf ./lib/gtk-2.0/2.10.0/immodules
rm -rf ./lib/gtk-2.0/2.10.0/loaders/*-{ani,bmp,gif,pcx,pnm,ras,tga,tiff,wbmp}.dll

# remove locales, keep the ones we have translations for
mkdir ./loc_tmp
mv ./share/locale/{de,fr,sv,it,pt,es,nl,ru,uk} ./loc_tmp/
rm -rf ./share/locale
mv ./loc_tmp/* ./share/locale/
rm -rf ./loc_tmp

# remove icons that are not needed
rm -rf ./share/icons/hicolor/scalable
rm -rf ./share/icons/hicolor/48x48
rm -rf ./share/icons/hicolor/24x24
rm -rf ./share/icons/hicolor/22x22
rm -rf ./share/icons/hicolor/8x8

# re-insert icons that _are_ needed indeed
mkdir -p share/icons/hicolor/scalable/status
mkdir -p share/icons/hicolor/48x48/apps

cp -v ${GTK_ROOT}/share/icons/hicolor/scalable/status/appointment-soon.svg share/icons/hicolor/scalable/status/
cp -v ${GTK_ROOT}/share/icons/hicolor/48x48/apps/palm-pilot-sync.png share/icons/hicolor/48x48/apps/
cp -v ${GTK_ROOT}/share/icons/hicolor/48x48/apps/config-date.png share/icons/hicolor/48x48/apps/

# pack dll files
#find -name '*.dll' -print0 | xargs -0 upx -9

cd ..
