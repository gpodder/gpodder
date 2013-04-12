# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

import os
import gpodder

_ = gpodder.gettext

from gpodder import util

import logging
logger = logging.getLogger(__name__)

class gPodderDevicePlaylist(object):
    def __init__(self, config, playlist_name):
        self._config=config
        self.linebreak = '\r\n'
        self.playlist_file=util.sanitize_filename(playlist_name + '.m3u')
        self.playlist_folder = os.path.join(self._config.device_sync.device_folder, self._config.device_sync.playlists.folder)
        self.mountpoint = util.find_mount_point(util.sanitize_encoding(self.playlist_folder))
        if self.mountpoint == '/':
            self.mountpoint = self.playlist_folder
            logger.warning('MP3 player resides on / - using %s as MP3 player root', self.mountpoint)
        self.playlist_absolute_filename=os.path.join(self.playlist_folder, self.playlist_file)

    def build_extinf(self, filename):
#TO DO: Windows playlists
#        if self._config.mp3_player_playlist_win_path:
#            filename = filename.replace('\\', os.sep)

#        # rebuild the whole filename including the mountpoint
#        if self._config.device_sync.playlist_absolute_path:
#            absfile = os.path.join(self.mountpoint,filename)
#        else: #TODO: Test rel filenames
#            absfile = util.rel2abs(filename, os.path.dirname(self.playlist_file))

        # fallback: use the basename of the file
        (title, extension) = os.path.splitext(os.path.basename(filename))

        return "#EXTINF:0,%s%s" % (title.strip(), self.linebreak)

    def read_m3u(self):
        """
        read all files from the existing playlist
        """
        tracks = []
        logger.info("Read data from the playlistfile %s" % self.playlist_absolute_filename)
        if os.path.exists(self.playlist_absolute_filename):
            for line in open(self.playlist_absolute_filename, 'r'):
                if not line.startswith('#EXT'):
                    tracks.append(line.rstrip('\r\n'))
        return tracks

    def get_filename_for_playlist(self, episode):
        """
        get the filename for the given episode for the playlist
        """
        filename_base = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        filename = filename_base + os.path.splitext(episode.local_filename(create=False))[1].lower()
        return filename

    def get_absolute_filename_for_playlist(self, episode):
        """
        get the filename including full path for the given episode for the playlist
        """
        filename = self.get_filename_for_playlist(episode)
        if self._config.device_sync.one_folder_per_podcast:
            filename = os.path.join(util.sanitize_filename(episode.channel.title), filename)
        if self._config.device_sync.playlist.absolute_path:
            filename = os.path.join(util.relpath(self.mountpoint, self._config.device_sync.device_folder), filename)
        return filename

    def write_m3u(self, episodes):
        """
        write the list into the playlist on the device
        """
        logger.info('Writing playlist file: %s', self.playlist_file)
        if not util.make_directory(self.playlist_folder):
            raise IOError(_('Folder %s could not be created.') % self.playlist_folder, _('Error writing playlist'))
        else:
            fp = open(os.path.join(self.playlist_folder, self.playlist_file), 'w')
            fp.write('#EXTM3U%s' % self.linebreak)
            for current_episode in episodes:
                filename_base = util.sanitize_filename(current_episode.sync_filename(
                    self._config.device_sync.custom_sync_name_enabled,
                    self._config.device_sync.custom_sync_name),
                    self._config.device_sync.max_filename_length)
                filename = filename_base + os.path.splitext(current_episode.local_filename(create=False))[1].lower()
                filename = self.get_filename_for_playlist(current_episode)
                fp.write(self.build_extinf(filename))
                filename = self.get_absolute_filename_for_playlist(current_episode)
                fp.write(filename)
                fp.write(self.linebreak)
            fp.close()

