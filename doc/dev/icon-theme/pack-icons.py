#!/usr/bin/python

import os
import sys
import glob
import shutil

THEMES = [
        '/usr/share/icons/gnome/',
        glob.glob('/home/thp/yo/gtk+*/gtk/stock-icons/')[0],
]

DESTDIR = '.'

icons = open('names', 'r').read().splitlines()

for theme in THEMES:
    if not os.path.isdir(theme):
        print >>sys.stderr, 'Skipping:', theme
        continue
    for source, dirnames, filenames in os.walk(theme):
        base_path = source[len(theme):]
        target = os.path.join(DESTDIR, base_path)
        for file in filenames:
            basename, extension = os.path.splitext(file)
            if basename in icons and \
                    'scalable' not in base_path and \
                    extension.lower() in ('.png', '.svg'):
                if not os.path.exists(target):
                    os.makedirs(target)
                shutil.copy(os.path.join(source, file), \
                        os.path.join(target, file))
                print os.path.join(target, file)

