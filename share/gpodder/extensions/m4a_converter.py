# -*- coding: utf-8 -*-
# Convertes m4a audio files to mp3
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-11-23 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import shlex
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Converts M4A audio')
__description__ = _('Converts m4a audio files to mp3')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


DefaultConfig = {
    'extensions': {
        'm4a_converter': {
            'file_format': [ True, False ],
            'context_menu': True,
        }
    }
}

FILE_FORMATS = ( 'mp3', 'ogg' )
FFMPEG_CMD = 'ffmpeg -i "%(infile)s" -sameq "%(outfile)s"'
MIME_TYPES = ['audio/x-m4a', 'audio/mp4']


class gPodderExtension:
    def __init__(self, container):
        self.container = container

        program = shlex.split(FFMPEG_CMD)[0]
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

        if not [e for e in episodes if e.mime_type in MIME_TYPES and e.file_exists()]:
            return None

        return [(self.container.metadata.title, self._convert_episodes)]

    def _convert_episode(self, episode):
        retvalue = self._run_conversion(episode)

        if retvalue == 0:
            logger.info('m4a -> %s conversion successful.', extension)
            gpodder.user_extensions.on_notification_show("Converting finished", episode)
            if not self.container.manager.testrun:
                self.rename_episode_file(episode, target)
                os.remove(filename)
        else:
            logger.info('Error converting file. FFMPEG installed?')
            gpodder.user_extensions.on_notification_show("Converting finished with errors", episode)
            try:
                os.remove(target)
            except OSError:
                pass

    def _run_conversion(self, episode):
        choices = zip(FILE_FORMATS, self.container.config.file_format)
        extension = '.' + [ext for ext, state in choices if state][0]

        filename = episode.local_filename(create=False)
        dirname = os.path.dirname(filename)
        basename, ext = os.path.splitext(os.path.basename(filename))
        new_filename = basename + extension

        if episode.mime_type not in MIME_TYPES:
            return

        gpodder.user_extensions.on_notification_show("Converting", episode)

        target = os.path.join(dirname, new_filename)
        cmd = FFMPEG_CMD % {
            'infile': filename,
            'outfile': target
        }

        # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
        cmd = util.sanitize_encoding(cmd)

        ffmpeg = subprocess.Popen(shlex.split(cmd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = ffmpeg.communicate()
        return ffmpeg.returncode

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)
