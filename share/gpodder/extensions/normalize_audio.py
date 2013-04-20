# -*- coding: utf-8 -*-
# This extension adjusts the volume of audio files to a standard level
# Supported file formats are mp3 and ogg
#
# Requires: normalize-audio, mpg123
#
# (c) 2011-11-06 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Normalize audio with re-encoding')
__description__ = _('Normalize the volume of audio files with normalize-audio')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/NormalizeAudio'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/NormalizeAudio'
__category__ = 'post-download'


DefaultConfig = {
    'context_menu': True, # Show action in the episode list context menu
}

# a tuple of (extension, command)
CONVERT_COMMANDS = {
    '.ogg': 'normalize-ogg',
    '.mp3': 'normalize-mp3',
}

class gPodderExtension:
    MIME_TYPES = ('audio/mpeg', 'audio/ogg', )
    EXT = ('.mp3', '.ogg', )

    def __init__(self, container):
        self.container = container

        # Dependency check
        self.container.require_command('normalize-ogg')
        self.container.require_command('normalize-mp3')
        self.container.require_command('normalize-audio')

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.container.config.context_menu:
            return None

        if not any(self._check_source(episode) for episode in episodes):
            return None

        return [(self.container.metadata.title, self.convert_episodes)]

    def _check_source(self, episode):
        if not episode.file_exists():
            return False

        if episode.mime_type in self.MIME_TYPES:
            return True

        if episode.extension() in self.EXT:
            return True

        return False

    def _convert_episode(self, episode):
        if episode.file_type() != 'audio':
            return

        filename = episode.local_filename(create=False)
        if filename is None:
            return

        basename, extension = os.path.splitext(filename)

        cmd = [CONVERT_COMMANDS.get(extension, 'normalize-audio'), filename]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        if p.returncode == 0:
            logger.info('normalize-audio processing successful.')
            gpodder.user_extensions.on_notification_show(_('File normalized'),
                    episode.title)
        else:
            logger.warn('normalize-audio failed: %s / %s', stdout, stderr)

    def convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

