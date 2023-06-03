#!/usr/bin/env python3
# create-desktop-icon.py: Create a Desktop icon
# 2016-12-22 Thomas Perl <m@thp.io>

import os
import sys
from pathlib import Path

from gi.repository import GLib

BASE = (Path(__file__).parent / '..').resolve()

TEMPLATE = """# Created by %(__file__)s
[Desktop Entry]
Name=gPodder (Git)
Exec=%(BASE)s/bin/gpodder
Icon=%(BASE)s/share/icons/hicolor/scalable/apps/gpodder.svg
Terminal=false
Type=Application
""" % locals()

DESKTOP = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)

if not Path(DESKTOP).exists():
    print("{} desktop folder doesn't exists, exiting".format(DESKTOP))
    sys.exit(1)

DESTINATION = os.path.join(DESKTOP, 'gpodder-git.desktop')

if Path(DESTINATION).exists():
    print('{} already exists, not overwriting'.format(DESTINATION))
    sys.exit(1)

with open(DESTINATION, 'w') as fp:
    fp.write(TEMPLATE)
os.chmod(DESTINATION, 0o755)

print('Wrote {}'.format(DESTINATION))
