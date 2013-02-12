# -*- coding: utf-8 -*-
# Convertes ogg audio files to mp3
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2012-12-28 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert OGG audio to MP3')
__description__ = _('Transcode .ogg files to .mp3 using ffmpeg')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__category__ = 'post-download'


DefaultConfig = {
    'context_menu': True, # Show the conversion option in the context menu
}

class gPodderExtension:
    MIME_TYPES = ('audio/ogg',)
    TARGET_EXT = '.mp3'

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.container.require_command('ffmpeg')

    def on_episode_downloaded(self, episode):
        self.convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(e.mime_type in self.MIME_TYPES for e in episodes):
            return None

        return [('Convert to MP3', self.convert_episodes)]

    def convert_episode(self, episode):
        if episode.mime_type not in self.MIME_TYPES:
            return

        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + self.TARGET_EXT

        cmd = ['ffmpeg', '-i', old_filename, '-qscale', '2', new_filename]
        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:            
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted OGG file to MP3.')
            gpodder.user_extensions.on_notification_show(_('File converted from ogg to mp3'), episode.title)
        else:
            logger.warn('Error converting file from ogg to mp3: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed from ogg to mp3'), episode.title)

    def convert_episodes(self, episodes):
        for episode in episodes:
            self.convert_episode(episode)

