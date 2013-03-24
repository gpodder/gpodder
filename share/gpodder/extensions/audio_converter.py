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

__title__ = _('Convert audio files')
__description__ = _('Transcode audio files to mp3/ogg')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/AudioConverter'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/AudioConverter'
__category__ = 'post-download'


DefaultConfig = {
    'use_ogg': False, # Set to True to convert to .ogg (otherwise .mp3)
    'context_menu': True, # Show the conversion option in the context menu
}

class gPodderExtension:
    MIME_TYPES = ('audio/x-m4a', 'audio/mp4', 'audio/mp4a-latm', 'audio/ogg', )
    EXT = ('.m4a', '.ogg')
    CMD = {'avconv': {'.mp3': ['-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-i', '%(old_file)s', '-q:a', '2', '%(new_file)s']
                     },
           'ffmpeg': {'.mp3': ['-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-i', '%(old_file)s', '-q:a', '2', '%(new_file)s']
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
        return ('.ogg' if self.config.use_ogg else '.mp3')

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

        target_format = ('OGG' if self.config.use_ogg else 'MP3')
        menu_item = _('Convert to %(format)s') % {'format': target_format}

        return [(menu_item, self._convert_episodes)]

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

        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted audio file to %(format)s.' % {'format': new_extension})
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warn('Error converting audio file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)
