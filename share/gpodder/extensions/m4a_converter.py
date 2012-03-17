# -*- coding: utf-8 -*-
# Convertes m4a audio files to mp3
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-11-23 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert M4A audio to MP3 or OGG')
__description__ = _('Transcode .m4a files to .mp3 or .ogg using ffmpeg')
__author__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'


DefaultConfig = {
    'use_ogg': False, # Set to True to convert to .ogg (otherwise .mp3)
    'context_menu': True, # Show the conversion option in the context menu
}

class gPodderExtension:
    MIME_TYPES = ['audio/x-m4a', 'audio/mp4']

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.container.require_command('ffmpeg')

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(e.mime_type in self.MIME_TYPES for e in episodes):
            return None

        target_format = ('OGG' if self.config.use_ogg else 'MP3')
        menu_item = _('Convert to %(format)s') % {'format': target_format}

        return [(menu_item, self._convert_episodes)]

    def _convert_episode(self, episode):
        if episode.mime_type not in self.MIME_TYPES:
            return

        if self.config.use_ogg:
            extension = '.ogg'
        else:
            extension = '.mp3'

        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + extension

        cmd = ['ffmpeg', '-i', old_filename, '-sameq', new_filename]
        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            logger.info('Converted M4A file.')
            gpodder.user_extensions.on_notification_show(_('File converted'), episode)
        else:
            logger.warn('Error converting file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

