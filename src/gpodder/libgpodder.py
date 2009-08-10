# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
#  libgpodder.py -- gpodder configuration
#  thomas perl <thp@perli.net>   20051030
#
#

import shutil
from collections import defaultdict

import gpodder
from gpodder import util
from gpodder import config
from gpodder import dbsqlite

import os
import glob
import subprocess

from liblogger import log

_ = gpodder.gettext


class gPodderLib(object):
    def __init__( self):
        util.make_directory(gpodder.home)
        self.config = config.Config(gpodder.config_file)

        if gpodder.interface == gpodder.MAEMO:
            # Detect changing of SD cards between mmc1/mmc2 if a gpodder
            # folder exists there (allow moving "gpodder" between SD cards or USB)
            # Also allow moving "gpodder" to home folder (e.g. rootfs on SD)
            if not os.path.exists(self.config.download_dir):
                log('Downloads might have been moved. Trying to locate them...', sender=self)
                for basedir in ['/media/mmc1', '/media/mmc2']+glob.glob('/media/usb/*')+['/home/user']:
                    dir = os.path.join(basedir, 'gpodder')
                    if os.path.exists(dir):
                        log('Downloads found in: %s', dir, sender=self)
                        self.config.download_dir = dir
                        break
                    else:
                        log('Downloads NOT FOUND in %s', dir, sender=self)

    def clean_up_downloads(self, delete_partial=False):
        # Clean up temporary files left behind by old gPodder versions
        temporary_files = glob.glob('%s/*/.tmp-*' % self.config.download_dir)

        if delete_partial:
            temporary_files += glob.glob('%s/*/*.partial' % self.config.download_dir)

        for tempfile in temporary_files:
            util.delete_file(tempfile)

        # Clean up empty download folders and abandoned download folders
        download_dirs = glob.glob(os.path.join(self.config.download_dir, '*'))
        for ddir in download_dirs:
            if os.path.isdir(ddir) and False: # FIXME not db.channel_foldername_exists(os.path.basename(ddir)):
                globr = glob.glob(os.path.join(ddir, '*'))
                if len(globr) == 0 or (len(globr) == 1 and globr[0].endswith('/cover')):
                    log('Stale download directory found: %s', os.path.basename(ddir), sender=self)
                    shutil.rmtree(ddir, ignore_errors=True)

    def streaming_possible(self):
        return self.config.player and self.config.player != 'default'

    def playback_episodes(self, episodes):
        groups = defaultdict(list)
        for episode in episodes:
            # Mark episode as played in the database
            episode.mark(is_played=True)

            file_type = episode.file_type()
            if file_type == 'video' and self.config.videoplayer and \
                    self.config.videoplayer != 'default':
                player = self.config.videoplayer
            elif file_type == 'audio' and self.config.player and \
                    self.config.player != 'default':
                player = self.config.player
            else:
                player = 'default'

            filename = episode.local_filename(create=False)
            if filename is None or not os.path.exists(filename):
                filename = episode.url
            groups[player].append(filename)

        # Open episodes with system default player
        if 'default' in groups:
            for filename in groups['default']:
                log('Opening with system default: %s', filename, sender=self)
                util.gui_open(filename)
            del groups['default']

        # For each type now, go and create play commands
        for group in groups:
            for command in util.format_desktop_command(group, groups[group]):
                log('Executing: %s', repr(command), sender=self)
                subprocess.Popen(command)

# Global, singleton gPodderLib object (for now)
gl = gPodderLib()

# Global, singleton Database object (for now)
db = dbsqlite.Database(gpodder.database_file)

