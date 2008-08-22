#!/usr/bin/python
#
# gPodder download folder sync (gdfs-init.py)
# Copyright 2007 Thomas Perl <thp@perli.net>
#
# Support for native language encodings by Leonid Ponomarev
#
# This file is distributed under the same terms
# as the gPodder program itself (GPLv3 or later).
#

import gettext
gettext.install('')

import gpodder.libpodcasts

import os.path
import shutil
import sys
import re

# Try to detect OS encoding (by Leonid Ponomarev)
if 'LANG' in os.environ and '.' in os.environ['LANG']:
    lang = os.environ['LANG']
    enc = lang.split('.')[-1]
else:
    print >>sys.stderr, 'Warning: No encoding detected in environment ($LANG).'
    print >>sys.stderr, 'Warning: Defaulting to iso-8859-1 encoding.'
    enc = 'iso-8859-1'

def cb_url( url):
    print 'Loading %s...' % url

if len(sys.argv) < 2:
    print >> sys.stderr, """
    Usage: %s [--yes] [Podcasts dir]

        Populates "Podcasts dir" with hard links from gPodder's
        downloads folder. "Podcasts dir" should be on the same
        filesystem as the downloads folder, and the filesystem
        has to support hard links.

        If "Podcasts dir" already exists, the script will ask 
        to overwrite its contents and re-build the mirror.

        The optional "--yes" parameter will skip the overwrite
        question and foribly re-build the folder if it exists.
    """ % os.path.basename( sys.argv[0])
    sys.exit( -1)

dest_dir = sys.argv[-1]

if os.path.exists( dest_dir):
    if '--yes' not in sys.argv and (raw_input( '"%s" exists, remove and rebuild? [y|N] ' % ( os.path.abspath( dest_dir), )).strip().lower()+'n')[0] != 'y':
        sys.exit( -1)
    shutil.rmtree( dest_dir)

for channel in gpodder.libpodcasts.load_channels():
    print channel.title
    channel_dir = os.path.join( dest_dir, os.path.basename( channel.title.replace('/', '-')))

    for episode in channel.get_all_episodes():
        episode_file = os.path.join( channel_dir, os.path.basename( episode.title.replace('/', '-')))
        filename = episode.local_filename()
        episode_file += os.path.splitext( os.path.basename( filename))[1]
        episode_file = re.sub('[|?*<>:+\[\]\"\\\]*', '', episode_file.encode(enc, 'ignore'))
        if os.path.exists( filename):
            channel_dir = re.sub('[|?*<>:+\[\]\"\\\]*', '', channel_dir.encode(enc, 'ignore'))
            if not os.path.exists( channel_dir):
                os.makedirs( channel_dir)

            # If the file exists, another episode already has
            # taken that file name, so look for a better one here
            # by appending " (2)", " (3)", etc..
            # (based on a patch by Mel Jay)
            _pfx = 1
            _dirn, _fnam = os.path.split(episode_file)
            _fnam, _ext = os.path.splitext(_fnam)
            while os.path.exists(episode_file):
                _pfx += 1
                episode_file = "%s/%s (%d)%s" % (_dirn, _fnam, _pfx, _ext)

            print '     Linking: ' + episode.title.encode(enc, 'ignore')
            os.link(filename, episode_file)

print """
    Yay, finished linking episodes :)

    You should now be able to browse and use your episodes in

       %s

    just as you would in a normal file system. When you have 
    downloaded new episodes, run this script again to rebuild
    this folder. If you delete episodes in that directory, 
    run gdfs-check.py on it to see which files you need to 
    delete inside the gPodder download directory to completely
    remove the episode from your hard disk.
""" % ( os.path.abspath( dest_dir), )

