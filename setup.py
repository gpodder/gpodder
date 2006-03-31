#!/usr/bin/env python

# gPodder setup script


import glob
import os
from distutils.core import setup


# read the version from the gpodder main program
gpodder_version = os.popen( "cat bin/gpodder |grep ^__version__.*=|cut -d\\\" -f2").read().strip()


inst_manpages = glob.glob( 'doc/man/*.1')
inst_images   = [ 'data/gpodder.png' ]
inst_share    = [ 'data/gpodder.glade' ]
inst_icons    = [ 'data/gpodder.desktop' ]
# TODO: install locales!!

data_files = [
  ('share/man/man1',       inst_manpages),
  ('share/gpodder/images', inst_images),
  ('share/gpodder',        inst_share),
  ('share/applications',   inst_icons)
]


setup(
  name         = 'gPodder',
  version      = gpodder_version,
  package_dir  = { '':'src' },
  packages     = [ 'gpodder' ],
  description  = 'Media Aggregator',
  author       = 'Thomas Perl',
  author_email = 'thp@perli.net',
  url          = 'http://perli.net/projekte/gpodder/',
  scripts      = [ 'bin/gpodder' ],
  data_files   = data_files
)

