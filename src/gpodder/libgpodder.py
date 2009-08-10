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
from gpodder import opml
from gpodder import config
from gpodder.dbsqlite import db

import os
import os.path
import glob
import types
import subprocess
import sys

from liblogger import log

_ = gpodder.gettext


class gPodderLib(object):
    def __init__( self):
        log('Creating gPodderLib()', sender=self)
        gpodder_dir = os.path.expanduser(os.path.join('~', '.config', 'gpodder'))
        if gpodder.interface == gpodder.MAEMO:
            old_dir = '/media/mmc2/gpodder/'
            if os.path.exists(os.path.join(old_dir, 'channels.opml')) and not os.path.exists(os.path.join(gpodder_dir, 'channels.opml')):
                # migrate from old (0.13.0 and earlier) gpodder maemo versions
                # to the current one by moving config files from mmc2 to $HOME
                util.make_directory(gpodder_dir)
                for filename in ('channels.opml', 'database.sqlite', 'gpodder.conf'):
                    try:
                        shutil.move(os.path.join(old_dir, filename), os.path.join(gpodder_dir, filename))
                    except:
                        log('Cannot move %s from %s to %s!', filename, old_dir, gpodder_dir, sender=self, traceback=True)
                if os.path.exists(os.path.join(old_dir, 'downloads')):
                    log('Moving old downloads')
                    # move old download location to new one
                    for folder in glob.glob(os.path.join(old_dir, 'downloads', '*')):
                        try:
                            shutil.move(folder, os.path.join(old_dir, os.path.basename(folder)))
                        except:
                            log('Cannot move %s to %s!', folder, old_dir, sender=self, traceback=True)
                    try:
                        os.rmdir(os.path.join(old_dir, 'downloads'))
                    except:
                        log('Cannot remove old folder %s!', os.path.join(old_dir, 'downloads'), traceback=True)

        util.make_directory(gpodder_dir)

        self.tempdir = gpodder_dir
        self.channel_settings_file = os.path.join(gpodder_dir, 'channelsettings.pickle.db')

        self.channel_opml_file = os.path.join(gpodder_dir, 'channels.opml')

        self.config = config.Config( os.path.join( gpodder_dir, 'gpodder.conf'))

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

        # We need to make a seamless upgrade, so by default the video player is not specified
        # so the first time this application is run it will detect this and set it to the same 
        # as the audio player.  This keeps gPodder functionality identical to that prior to the 
        # upgrade.   The user can then set a specific video player if they so wish.	
        if self.config.videoplayer == 'unspecified':
            self.config.videoplayer = self.config.player	

        self.bluetooth_available = util.bluetooth_available()

        self.gpodder_dir = gpodder_dir
        not db.setup({ 'database': os.path.join(gpodder_dir, 'database.sqlite'), 'gl': self })

    def get_device_name( self):
        if self.config.device_type == 'ipod':
            return _('iPod')
        elif self.config.device_type in ('filesystem', 'mtp'):
            return _('MP3 player')
        else:
            log( 'Warning: Called get_device_name() when no device was selected.', sender = self)
            return '(unknown device)'

    def find_partial_files(self):
        return glob.glob(os.path.join(self.downloaddir, '*', '*.partial'))

    def clean_up_downloads(self, delete_partial=False):
        # Clean up temporary files left behind by old gPodder versions
        temporary_files = glob.glob('%s/*/.tmp-*' % self.downloaddir)

        if delete_partial:
            temporary_files += glob.glob('%s/*/*.partial' % self.downloaddir)

        for tempfile in temporary_files:
            util.delete_file(tempfile)

        # Clean up empty download folders and abandoned download folders
        download_dirs = glob.glob(os.path.join(self.downloaddir, '*'))
        for ddir in download_dirs:
            if os.path.isdir(ddir) and not db.channel_foldername_exists(os.path.basename(ddir)):
                globr = glob.glob(os.path.join(ddir, '*'))
                if len(globr) == 0 or (len(globr) == 1 and globr[0].endswith('/cover')):
                    log('Stale download directory found: %s', os.path.basename(ddir), sender=self)
                    shutil.rmtree(ddir, ignore_errors=True)

    def get_download_dir( self):
        util.make_directory( self.config.download_dir)
        return self.config.download_dir

    def set_download_dir( self, new_downloaddir):
        if self.config.download_dir != new_downloaddir:
            log( 'Moving downloads from %s to %s', self.config.download_dir, new_downloaddir)
            try:
                # Fix error when moving over disk boundaries
                if os.path.isdir( new_downloaddir) and not os.listdir( new_downloaddir):
                    os.rmdir( new_downloaddir)

                shutil.move( self.config.download_dir, new_downloaddir)
            except NameError:
                log( 'Fixing a bug in shutil. See http://bugs.python.org/issue2549')
                errno = subprocess.call(["rm", "-rf", self.config.download_dir])
                if errno <> 0:
                    log( 'Error while deleting %s: rm returned error %i', self.config.download_dir, errno) 
                    return
            except Exception, exc:
                log( 'Error while moving %s to %s: %s',self.config.download_dir, new_downloaddir, exc)
                return

        self.config.download_dir = new_downloaddir

    downloaddir = property(fget=get_download_dir,fset=set_download_dir)
    
    def send_subscriptions(self):
        try:
            subprocess.Popen(['xdg-email', '--subject', _('My podcast subscriptions'),
                                           '--attach', self.channel_opml_file])
        except:
            return False
        
        return True

    def streaming_possible(self):
        return self.config.player and self.config.player != 'default'

    def playback_episodes(self, episodes):
        groups = defaultdict(list)
        for episode in episodes:
            # Mark all episodes as played in the database
            db.mark_episode(episode.url, is_played=True)

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

# Global, singleton gPodderLib object
gl = gPodderLib()


