#!/usr/bin/env python2.4

#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2006 Thomas Perl <thp at perli.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, 
# MA  02110-1301, USA.
#

import glob
import os
from distutils.core import setup


# read the version from the gpodder main program
gpodder_version = os.popen( "cat bin/gpodder |grep ^__version__.*=|cut -d\\\" -f2").read().strip()

# translations
languages = [ "de", "fr", "sv", "it", "pt" ]
translation_files = []

# add translated files to translations dictionary
for l in languages:
    translation_files.append( ("share/locale/%s/LC_MESSAGES" % l, [ "data/locale/%s/LC_MESSAGES/gpodder.mo" % l ]) )

# files to install
inst_manpages = glob.glob( 'doc/man/*.1')
inst_images   = glob.glob('data/artwork/*')
inst_icons    = [ 'data/gpodder.png' ] + glob.glob('data/gpodder-??x??.png')
inst_share    = [ 'data/gpodder.glade', 'data/gpodder-48x48.png' ]
inst_desktop  = [ 'data/gpodder.desktop' ]

data_files = [
  ('share/man/man1',       inst_manpages),
  ('share/gpodder/images', inst_images),
  ('share/gpodder',        inst_share),
  ('share/applications',   inst_desktop),
  ('share/pixmaps',        inst_icons),
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

