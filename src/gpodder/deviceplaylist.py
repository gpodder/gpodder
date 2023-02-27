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

import logging
import os

import gpodder
from gpodder import util
from gpodder.sync import (episode_filename_on_device,
                          episode_foldername_on_device)

import gi  # isort:skip
gi.require_version('Gio', '2.0')  # isort:skip
from gi.repository import Gio, GLib  # isort:skip

_ = gpodder.gettext


logger = logging.getLogger(__name__)


class gPodderDevicePlaylist(object):
    def __init__(self, config, playlist_name):
        self._config = config
        self.linebreak = '\r\n'
        self.playlist_file = (util.sanitize_filename(playlist_name, self._config.device_sync.max_filename_length) +
                             '.' + self._config.device_sync.playlists.extension)
        device_folder = util.new_gio_file(self._config.device_sync.device_folder)
        self.playlist_folder = device_folder.resolve_relative_path(self._config.device_sync.playlists.folder)

        self.mountpoint = None
        try:
            self.mountpoint = self.playlist_folder.find_enclosing_mount().get_root()
        except GLib.Error as err:
            logger.error('find_enclosing_mount folder %s failed: %s', self.playlist_folder.get_uri(), err.message)

        if not self.mountpoint:
            self.mountpoint = self.playlist_folder
            logger.warning('could not find mount point for MP3 player - using %s as MP3 player root', self.mountpoint.get_uri())
        self.playlist_absolute_filename = self.playlist_folder.resolve_relative_path(self.playlist_file)

    def build_extinf(self, filename):
        # TODO: Windows playlists
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
        logger.info("Read data from the playlistfile %s" % self.playlist_absolute_filename.get_uri())
        if self.playlist_absolute_filename.query_exists():
            stream = Gio.DataInputStream.new(self.playlist_absolute_filename.read())
            while True:
                line = stream.read_line_utf8()[0]
                if not line:
                    break
                if not line.startswith('#EXT'):
                    tracks.append(line.rstrip('\r\n'))
            stream.close()
        return tracks

    def get_filename_for_playlist(self, episode):
        """
        get the filename for the given episode for the playlist
        """
        return episode_filename_on_device(self._config, episode)

    def get_absolute_filename_for_playlist(self, episode):
        """
        get the filename including full path for the given episode for the playlist
        """
        filename = self.get_filename_for_playlist(episode)
        foldername = episode_foldername_on_device(self._config, episode)
        if foldername:
            filename = os.path.join(foldername, filename)
        if self._config.device_sync.playlists.use_absolute_path:
            filename = os.path.join(util.relpath(self._config.device_sync.device_folder, self.mountpoint.get_uri()), filename)
        return filename

    def write_m3u(self, episodes):
        """
        write the list into the playlist on the device
        """
        logger.info('Writing playlist file: %s', self.playlist_file)
        if not util.make_directory(self.playlist_folder):
            raise IOError(_('Folder %s could not be created.') % self.playlist_folder, _('Error writing playlist'))
        else:
            # work around libmtp devices potentially having limited capabilities for partial writes
            is_mtp = self.playlist_folder.get_uri().startswith("mtp://")
            tempfile = None
            if is_mtp:
                tempfile = Gio.File.new_tmp()
                fs = tempfile[1].get_output_stream()
            else:
                fs = self.playlist_absolute_filename.replace(None, False, Gio.FileCreateFlags.NONE)

            os = Gio.DataOutputStream.new(fs)
            os.put_string('#EXTM3U%s' % self.linebreak)
            for current_episode in episodes:
                filename = self.get_filename_for_playlist(current_episode)
                os.put_string(self.build_extinf(filename))
                filename = self.get_absolute_filename_for_playlist(current_episode)
                os.put_string(filename)
                os.put_string(self.linebreak)
            os.close()

            if is_mtp:
                try:
                    tempfile[0].copy(self.playlist_absolute_filename, Gio.FileCopyFlags.OVERWRITE)
                except GLib.Error as err:
                    logger.error('copying playlist to mtp device file %s failed: %s',
                        self.playlist_absolute_filename.get_uri(), err.message)
                tempfile[0].delete()
