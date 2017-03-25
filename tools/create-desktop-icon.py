#!/usr/bin/env python
# create-desktop-icon.py: Create a Desktop icon
# 2016-12-22 Thomas Perl <m@thp.io>

import os
import sys

BASE = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TEMPLATE = """# Created by %(__file__)s
[Desktop Entry]
Name=gPodder (Git)
Exec=%(BASE)s/bin/gpodder
Icon=%(BASE)s/share/icons/hicolor/scalable/apps/gpodder.svg
Terminal=false
Type=Application
""" % locals()

DESTINATION = os.path.expanduser('~/Desktop/gpodder-git.desktop')

if os.path.exists(DESTINATION):
    print('%(DESTINATION)s already exists, not overwriting')
    sys.exit(1)

with open(DESTINATION, 'w') as fp:
    fp.write(TEMPLATE)
os.chmod(DESTINATION, 0o755)

print('Wrote %(DESTINATION)s' % locals())
