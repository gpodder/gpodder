#!/usr/bin/env python

# gPodder setup script


import glob
import os
from distutils.core import setup


# read the version from the gpodder main program
gpodder_version = os.popen( "cat bin/gpodder |grep ^__version__.*=|cut -d\\\" -f2").read().strip()

# translations
languages = [ "de", "fr" ]
translation_files = []

# add translated files to translations dictionary
for l in languages:
    translation_files.append( ("share/locale/%s/LC_MESSAGES" % l, [ "data/locale/%s/LC_MESSAGES/gpodder.mo" % l ]) )

# files to install
inst_manpages = glob.glob( 'doc/man/*.1')
inst_images   = [ 'data/gpodder.png' ] + glob.glob('data/artwork/*')
inst_share    = [ 'data/gpodder.glade' ]
inst_icons    = [ 'data/gpodder.desktop' ]

data_files = [
  ('share/man/man1',       inst_manpages),
  ('share/gpodder/images', inst_images),
  ('share/gpodder',        inst_share),
  ('share/applications',   inst_icons),
]

setup(
  name         = 'gpodder',
  version      = gpodder_version,
  package_dir  = { '':'src' },
  packages     = [ 'gpodder' ],
  description  = 'media aggregator',
  author       = 'Thomas Perl',
  author_email = 'thp@perli.net',
  url          = 'http://perli.net/projekte/gpodder/',
  scripts      = [ 'bin/gpodder' ],
  data_files   = data_files + translation_files
)

