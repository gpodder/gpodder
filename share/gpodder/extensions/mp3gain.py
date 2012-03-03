# -*- coding: utf-8 -*-
# This extension adjusts mp3s so that they all have the same volume
#
# Requires: mp3gain
#
# (c) 2011-11-06 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.
import os
import platform
import shlex
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('mp3gain')
__description__ = _('This hook adjusts mp3s so that they all have the same volume. It don\'t decode and re-encode the audio file')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


DefaultConfig = {
    'extensions': {
        'mp3gain': {
            'context_menu': True,
        }
    }
}

CMD = {
    'Linux': 'mp3gain -c "%s"',
    'Windows': 'mp3gain.exe -c "%s"'
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container

        self.cmd = CMD[platform.system()]
        program = shlex.split(self.cmd)[0]
        if not util.find_command(program):
            raise ImportError("Couldn't find program '%s'" % program)

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.container.config.context_menu:
            return None

        if 'audio/mpeg' not in [e.mime_type for e in episodes
            if e.mime_type is not None and e.file_exists()]:
            return None

        return [(self.container.metadata.title, self._convert_episodes)]

    def _convert_episode(self, episode):
        filename = episode.local_filename(create=False, check_only=True)
        if filename is None:
            return

        (basename, extension) = os.path.splitext(filename)
        if episode.file_type() == 'audio' and extension.lower().endswith('mp3'):

            cmd = self.cmd % filename

            # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
            cmd = util.sanitize_encoding(cmd)

            p = subprocess.Popen(shlex.split(cmd),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()

            if p.returncode == 0:
                logger.info('mp3gain processing successfull.')

            else:
                logger.info('mp3gain processing not successfull.')
                logger.debug(stdout + stderr)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)
