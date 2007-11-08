#!/usr/bin/python
#
# gPodder download folder sync (gdfs-check.py)
# Copyright 2007 Thomas Perl <thp@perli.net>
#
# This file is distributed under the same terms
# as the gPodder program itself (GPLv3 or later).
#

import gettext
gettext.install('')

from gpodder import libgpodder

import sys
import os
import os.path
import stat

def get_files_from( top_path):
    result = {}

    for ( dirpath, dirnames, filenames ) in os.walk( os.path.abspath( top_path)):
        for filename in ( os.path.join( dirpath, filename) for filename in filenames ):
            s = os.stat( filename)
            if stat.S_ISREG(s[stat.ST_MODE]):
                device = s[stat.ST_DEV]
                inode = s[stat.ST_INO]
                result[(device,inode)] = filename

    return result

def filter_dict( d, keys_exclude):
    result = {}

    for key, value in d.items():
        if key not in keys_exclude:
            result[key] = value

    return result

def filter_gpodder_metadata( d):
    result = {}
    for key, value in d.items():
        if not value.endswith( '/cover') and not value.endswith('/index.xml'):
            result[key] = value

    return result

def usage():
    print >> sys.stderr, """
    Usage: %s [from-gpodder|from-podcasts] [Podcasts dir]

        If you have deleted episodes from your Podcast mirror
        folder, use "from-podcasts" to get a list of files 
        that you have to delete from gPodder's download
        folder to "sync" with your podcast mirror.

        If you have deleted episodes in gPodder, you can use
        "from-gpodder" to get a list of files that are still 
        available in your podcasts dir, but not in gPodder's
        download directory.
    """ % ( os.path.basename( sys.argv[0]), )

if len(sys.argv) != 3:
    usage()
    sys.exit( -1)

files_in_dir1 = get_files_from( libgpodder.gPodderLib().downloaddir)
files_in_dir2 = get_files_from( sys.argv[-1])

files_missing_in_dir2 = filter_gpodder_metadata( filter_dict( files_in_dir1, files_in_dir2.keys())).values()
files_missing_in_dir1 = filter_gpodder_metadata( filter_dict( files_in_dir2, files_in_dir1.keys())).values()

if sys.argv[1].find( 'from-podcasts') >= 0:
    if len( files_missing_in_dir2):
        print >> sys.stderr, 'Files in gPodder that are not in %s:' % sys.argv[-1]
        for filename in files_missing_in_dir2:
            print filename
    else:
        print >> sys.stderr, 'All files in gPodder are in %s, too.' % sys.argv[-1]
elif sys.argv[1].find( 'from-gpodder') >= 0:
    if len( files_missing_in_dir1):
        print >> sys.stderr, 'Files in %s that are not in gPodder:' % sys.argv[-1]
        for filename in files_missing_in_dir1:
            print filename
    else:
        print >> sys.stderr, 'All files in %s are in gPodder, too.' % sys.argv[-1]
else:
    usage()
    print >> sys.stderr, 'Not a valid operation: "%s" (use from-podcasts or from-gpodder)' % ( sys.argv[1], )


