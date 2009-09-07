#!/usr/bin/python

import os
import sys
import glob
import shutil
import collections

THEMES = [
        '/usr/share/icons/gnome/',
        glob.glob('/home/thp/yo/gtk+*/gtk/stock-icons/')[0],
]

DESTDIR = '.'

icons = open('names', 'r').read().splitlines()

copyright = collections.defaultdict(list)

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
                copy_from = os.path.join(source, file)
                copy_to = os.path.join(target, file)
                if not os.path.exists(target):
                    os.makedirs(target)
                shutil.copy(copy_from, copy_to)
                copyright[theme].append(copy_to)
                for theme_old in THEMES:
                    if theme_old != theme and copy_to in copyright[theme_old]:
                        print 'Replacing icon from', theme_old, 'with', theme
                        copyright[theme_old].remove(copy_to)
                print copy_to

out = open('copyright', 'w')
for theme in copyright:
    out.write('==== '+theme+' ====\n\n')
    for file in copyright[theme]:
        out.write(file+'\n')
    out.write('\n')
out.close()
