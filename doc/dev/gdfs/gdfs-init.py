#!/usr/bin/python
#
# gPodder download folder sync (gdfs-init.py)
# Copyright 2007 Thomas Perl <thp@perli.net>
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

for channel in gpodder.libpodcasts.load_channels( callback_url = cb_url, offline = True):
    print channel.title
    channel_dir = os.path.join( dest_dir, os.path.basename( channel.title))

    for episode in channel.get_all_episodes():
        episode_file = os.path.join( channel_dir, os.path.basename( episode.title))
        filename = episode.local_filename()
        episode_file += os.path.splitext( os.path.basename( filename))[1]
        if os.path.exists( filename):
            if not os.path.exists( channel_dir):
                os.makedirs( channel_dir)
            os.link( filename, episode_file)
            print '     Linking: ' + episode.title

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

