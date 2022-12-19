#!/usr/bin/env python3
# create-desktop-icon.py: Create a Desktop icon
# 2016-12-22 Thomas Perl <m@thp.io>

import os
import sys

from gi.repository import GLib

BASE = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TEMPLATE = """# Created by %(__file__)s
[Desktop Entry]
Name=gPodder (Git)
Exec=%(BASE)s/bin/gpodder
Icon=%(BASE)s/share/icons/hicolor/scalable/apps/gpodder.svg
Terminal=false
Type=Application
""" % locals()

DESKTOP = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)

if not os.path.exists(DESKTOP):
    print("{} desktop folder doesn't exists, exiting".format(DESKTOP))
    sys.exit(1)

DESTINATION = os.path.join(DESKTOP, 'gpodder-git.desktop')

if os.path.exists(DESTINATION):
    print('{} already exists, not overwriting'.format(DESTINATION))
    sys.exit(1)

with open(DESTINATION, 'w') as fp:
    fp.write(TEMPLATE)
os.chmod(DESTINATION, 0o755)

print('Wrote {}'.format(DESTINATION))
