# -*- coding: utf-8 -*-
# This extension adjusts mp3s so that they all have the same volume
#
# Requires: mp3gain
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

__title__ = _('mp3gain Volume Normalizer')
__description__ = _('Normalize the volume of MP3 files without re-encoding')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


DefaultConfig = {
    'context_menu': True,
}


class gPodderExtension:
    MIME_TYPE = 'audio/mpeg'

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        self.mp3gain = self.container.require_command('mp3gain')

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(e.mime_type == self.MIME_TYPE for e in episodes):
            return None

        return [(_('Normalize volume (mp3gain)'), self._convert_episodes)]

    def _convert_episode(self, episode):
        if episode.mime_type != self.MIME_TYPE:
            return

        filename = episode.local_filename(create=False)
        if filename is None:
            return

        cmd = [self.mp3gain, '-c', filename]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        if p.returncode == 0:
            logger.info('mp3gain processing successful.')
        else:
            logger.warn('mp3gain failed: %s / %s', stdout, stderr)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

