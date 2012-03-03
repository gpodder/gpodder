# -*- coding: utf-8 -*-
# This extension adjusts the volume of audio files to a standard level
# Supported file formats are mp3 and ogg
#
# Requires: normalize-audio, mpg123
#
# (c) 2011-11-06 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.
import os
import shlex
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Normalize audio')
__description__ = _('This hook adjusts mp3s/oggs so that they all have the same volume. It decode and re-encode the audio file')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


DefaultConfig = {
    'extensions': {
        'normalize_audio': {
            'context_menu': True,
        }
    }
}

# a tuple of (extension, command)
SUPPORTED = (('ogg', 'normalize-ogg "%s"'), ('mp3', 'normalize-mp3 "%s"'))

#TODO: add setting to use normalize-audio instead of normalizie-mp3 for mp3 files if wanted
# http://normalize.nongnu.org/README.html FAQ #5
#MP3_CMD = 'normalize-audio "%s"'

CMDS_TO_TEST = ('normalize-ogg', 'normalize-mp3', 'normalize-audio',
    'lame', 'mpg123', 'oggenc', 'oggdec')


class gPodderExtension:
    def __init__(self, container):
        self.container = container

        for cmd in CMDS_TO_TEST:
            program = shlex.split(cmd)[0]
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

        mimetypes = [e.mime_type for e in episodes
            if e.mime_type is not None and e.file_exists()]
        if 'audio/ogg' not in mimetypes and 'audio/mpeg' not in mimetypes:
            return None

        return [(self.container.metadata.title, self._convert_episodes)]

    def _convert_episode(self, episode):
        filename = episode.local_filename(create=False, check_only=True)
        if filename is None:
            return

        formats, commands = zip(*SUPPORTED)
        (basename, extension) = os.path.splitext(filename)
        extension = extension.lstrip('.').lower()
        if episode.file_type() == 'audio' and extension in formats:
            gpodder.user_extensions.on_notification_show("Normalizing", episode)

            cmd = commands[formats.index(extension)] % filename

            # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
            cmd = util.sanitize_encoding(cmd)

            p = subprocess.Popen(shlex.split(cmd),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()

            if p.returncode == 0:
                logger.info('normalize-audio processing successfull.')
                gpodder.user_extensions.on_notification_show("Normalizing finished successfully", episode)

            else:
                logger.info('normalize-audio processing not successfull.')
                gpodder.user_extensions.on_notification_show("Normalizing finished not successfully", episode)
                logger.debug(stderr)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)
