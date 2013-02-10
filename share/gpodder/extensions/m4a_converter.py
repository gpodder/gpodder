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
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert M4A audio to MP3 or OGG')
__description__ = _('Transcode .m4a files to .mp3 or .ogg using ffmpeg')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__category__ = 'post-download'


DefaultConfig = {
    'use_ogg': False, # Set to True to convert to .ogg (otherwise .mp3)
    'context_menu': True, # Show the conversion option in the context menu
}

class gPodderExtension:
    MIME_TYPES = ['audio/x-m4a', 'audio/mp4', 'audio/mp4a-latm']
    EXT = '.m4a'

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

        # add additional file-extension check (#bug1770)
        mimecheck = [e.mime_type in self.MIME_TYPES for e in episodes]
        extcheck = [e.local_filename(create=False).endswith(self.EXT) for e in episodes]
        if not any(mimecheck + extcheck):
            return None

        target_format = ('OGG' if self.config.use_ogg else 'MP3')
        menu_item = _('Convert to %(format)s') % {'format': target_format}

        return [(menu_item, self._convert_episodes)]

    def _convert_episode(self, episode):
        old_filename = episode.local_filename(create=False)

        # add additional file-extension check (#bug1770)
        if episode.mime_type not in self.MIME_TYPES and not old_filename.endswith(self.EXT):
            return

        if self.config.use_ogg:
            extension = '.ogg'
        else:
            extension = '.mp3'

        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + extension

        cmd = ['ffmpeg', '-i', old_filename, '-sameq', new_filename]
        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted M4A file.')
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warn('Error converting file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

