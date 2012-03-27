# -*- coding: utf-8 -*-
# Put FLV files from YouTube into a MP4 container after download
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files. This does not convert
# the files in reality, but just swaps the container format.
#
# (c) 2011-08-05 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder

from gpodder import util
from gpodder import youtube

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert .flv files from YouTube to .mp4')
__description__ = _('Useful for playing downloaded videos on hardware players')
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'

DefaultConfig = {
    'context_menu': True, # Show the conversion option in the context menu
}


class gPodderExtension:
    MIME_TYPE = 'video/x-flv'

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.container.require_command('ffmpeg')

    def on_episode_downloaded(self, episode):
        if youtube.is_video_link(episode.url):
            self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(e.mime_type == self.MIME_TYPE for e in episodes):
            return None

        return [(_('Convert FLV to MP4'), self._convert_episodes)]


    def _convert_episode(self, episode):
        old_filename = episode.local_filename(create=False)
        filename, ext = os.path.splitext(old_filename)
        new_filename = filename + '.mp4'

        if open(old_filename, 'rb').read(3) != 'FLV':
            logger.debug('Not a FLV file. Ignoring.')
            return

        if ext.lower() == '.mp4':
            # Move file out of place for conversion
            tmp_filename = filename + '.flv'
            os.rename(old_filename, tmp_filename)
            old_filename = tmp_filename

        cmd = ['ffmpeg',
                '-i', old_filename,
                '-vcodec', 'copy',
                '-acodec', 'copy',
                new_filename]

        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            logger.info('FLV conversion successful.')
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
        else:
            logger.warn('Error converting file: %s / %s', stdout, stderr)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

