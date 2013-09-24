# -*- coding: utf-8 -*-
# Convertes video files to avi or mp4
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-08-05 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder

from gpodder import util
from gpodder import youtube

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert video files')
__description__ = _('Transcode video files to avi/mp4/m4v')
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/VideoConverter'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/VideoConverter'
__category__ = 'post-download'

DefaultConfig = {
    'output_format': 'mp4', # At the moment we support/test only mp4, m4v and avi
    'context_menu': True, # Show the conversion option in the context menu
}


class gPodderExtension:
    MIME_TYPES = ('video/mp4', 'video/m4v', 'video/x-flv', )
    EXT = ('.mp4', '.m4v', '.flv', )
    CMD = {'avconv': ['-i', '%(old_file)s', '-codec', 'copy', '%(new_file)s'],
           'ffmpeg': ['-i', '%(old_file)s', '-codec', 'copy', '%(new_file)s']
          }

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.command = self.container.require_any_command(['avconv', 'ffmpeg'])

        # extract command without extension (.exe on Windows) from command-string
        command_without_ext = os.path.basename(os.path.splitext(self.command)[0])
        self.command_param = self.CMD[command_without_ext]

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)
        
    def _get_new_extension(self):
        ext = self.config.output_format
        if not ext.startswith('.'):
            ext = '.' + ext

        return ext

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

        menu_item = _('Convert to %(format)s') % {'format': self.config.output_format}

        return [(menu_item, self._convert_episodes)]

    def _convert_episode(self, episode):
        if not self._check_source(episode):
            return

        new_extension = self._get_new_extension()
        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + new_extension
        
        cmd = [self.command] + \
            [param % {'old_file': old_filename, 'new_file': new_filename}
                for param in self.command_param]
        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:            
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted video file to %(format)s.' % {'format': self.config.output_format})
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warn('Error converting video file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

