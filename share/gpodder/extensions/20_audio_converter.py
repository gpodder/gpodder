# -*- coding: utf-8 -*-
# Convertes m4a audio files to mp3
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-11-23 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import logging
import os
import subprocess

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert audio files')
__description__ = _('Transcode audio files to mp3/ogg')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'https://gpodder.github.io/docs/extensions/audioconverter.html'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/AudioConverter'
__category__ = 'post-download'


DefaultConfig = {
    'use_opus': False,  # Set to True to convert to .opus
    'use_ogg': False,  # Set to True to convert to .ogg
    'context_menu': True,  # Show the conversion option in the context menu
}


class gPodderExtension:
    MIME_TYPES = ('audio/x-m4a', 'audio/mp4', 'audio/mp4a-latm', 'audio/mpeg', 'audio/ogg', 'audio/opus')
    EXT = ('.m4a', '.ogg', '.opus', '.mp3')
    CMD = {'avconv': {'.mp3': ['-n', '-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-n', '-i', '%(old_file)s', '-q:a', '2', '%(new_file)s'],
                      '.opus': ['-n', '-i', '%(old_file)s', '-b:a', '64k', '%(new_file)s']
                      },
           'ffmpeg': {'.mp3': ['-n', '-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-n', '-i', '%(old_file)s', '-q:a', '2', '%(new_file)s'],
                      '.opus': ['-n', '-i', '%(old_file)s', '-b:a', '64k', '%(new_file)s']
                      }
           }

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.command = self.container.require_any_command(['avconv', 'ffmpeg'])

        # extract command without extension (.exe on Windows) from command-string
        self.command_without_ext = os.path.basename(os.path.splitext(self.command)[0])

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def _get_new_extension(self):
        if self.config.use_ogg:
            extension = '.ogg'
        elif self.config.use_opus:
            extension = '.opus'
        else:
            extension = '.mp3'
        return extension

    def _check_source(self, episode):
        if episode.extension() == self._get_new_extension():
            return False

        if episode.mime_type in self.MIME_TYPES:
            return True

        # Also check file extension (bug 1770)
        if episode.extension() in self.EXT:
            return True

        return False

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(self._check_source(episode) for episode in episodes):
            return None

        menu_item = _('Convert to %(format)s') % {'format': self._target_format()}

        return [(menu_item, self._convert_episodes)]

    def _target_format(self):
        if self.config.use_ogg:
            target_format = 'OGG'
        elif self.config.use_opus:
            target_format = 'OPUS'
        else:
            target_format = 'MP3'
        return target_format

    def _convert_episode(self, episode):
        if not self._check_source(episode):
            return

        new_extension = self._get_new_extension()
        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + new_extension

        cmd_param = self.CMD[self.command_without_ext][new_extension]
        cmd = [self.command] + \
            [param % {'old_file': old_filename, 'new_file': new_filename}
                for param in cmd_param]

        if gpodder.ui.win32:
            ffmpeg = util.Popen(cmd)
            ffmpeg.wait()
            stdout, stderr = ("<unavailable>",) * 2
        else:
            ffmpeg = util.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)

            logger.info('Converted audio file to %(format)s.' % {'format': new_extension})
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warning('Error converting audio file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        # not running in background because there is no feedback to the user
        # which one is being converted and nothing prevents from clicking convert twice.
        for episode in episodes:
            self._convert_episode(episode)
