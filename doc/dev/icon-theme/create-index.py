#!/usr/bin/python

ICON_THEME_NAME = 'gpodder'

import sys
import os
import glob
from ConfigParser import RawConfigParser

directories = glob.glob('*x*/*') + glob.glob('*x*/*/*')
directories = [d for d in directories if os.path.isdir(d)]

parser = RawConfigParser()

# Disable converting keys to lowercase
parser.optionxform = str

parser.add_section('Icon Theme')
parser.set('Icon Theme', 'Name', ICON_THEME_NAME)
parser.set('Icon Theme', 'Directories', ','.join(directories))

for directory in directories:
    size = directory[:directory.find('x')]
    context = directory.split('/')[1]
    parser.add_section(directory)
    parser.set(directory, 'Size', size)
    parser.set(directory, 'Context', context.capitalize())
    parser.set(directory, 'Type', 'Treshold')

parser.write(sys.stdout)

