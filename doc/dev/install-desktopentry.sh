#!/bin/sh
# Adds shortcuts to your Gnome menu to run and update
# the local Git checkout if the user wants to have it
# 2009-04-27 Thomas Perl <thp.io/about>

DESKTOPFILE=~/.local/share/applications/gpodder-git-version.desktop
DESKTOPFILE_UPDATER=~/.local/share/applications/gpodder-git-update.desktop
GITCHECKOUT=`pwd`

if [ "$1" = "--remove" ]; then
    echo "Removing: $DESKTOPFILE"
    rm -f "$DESKTOPFILE"
    echo "Removing: $DESKTOPFILE_UPDATER"
    rm -f "$DESKTOPFILE_UPDATER"
    exit 0
fi

# Make sure the folder where we install files exists
mkdir -p "`dirname "$DESKTOPFILE"`"

echo "Installing: $DESKTOPFILE"
cat data/gpodder.desktop | \
    sed -e "s#^Name\\([^=]*\\)=\\(.*\\)#Name\\1=\\2 (Git checkout in $GITCHECKOUT)#g" | \
    sed -e "s#^Exec=.*#Exec=$GITCHECKOUT/bin/gpodder#" | \
    sed -e "s#^Icon=.*#Icon=$GITCHECKOUT/data/gpodder.png#" \
    >"$DESKTOPFILE"

if [ ! -d "$GITCHECKOUT/.git" ]; then
    echo ".git directory not found - not installing updater shortcut."
    exit 0
fi

echo "Installing: $DESKTOPFILE_UPDATER"
cat >"$DESKTOPFILE_UPDATER" <<EOF
[Desktop Entry]
Name=gPodder Podcast Client (Updater for $GITCHECKOUT)
Exec=python $GITCHECKOUT/doc/dev/update-git-gui.py
Comment=Updates the local Git checkout of gPodder located in $GITCHECKOUT
Terminal=false
Type=Application
Categories=AudioVideo;Audio;FileTransfer;News;GTK;
EOF

