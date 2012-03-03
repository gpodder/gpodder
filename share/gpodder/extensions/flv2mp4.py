# -*- coding: utf-8 -*-
# Put FLV files from YouTube into a MP4 container after download
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files. This does not convert
# the files in reality, but just swaps the container format.
#
# (c) 2011-08-05 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import os
import shlex
import subprocess

import gpodder
from gpodder import util
from gpodder import youtube

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert FLV to MP4')
__description__ = _('Put FLV files from YouTube into a MP4 container after download')
__author__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'

DefaultConfig = {
    'extensions': {
        'flv2mp4': {
            'context_menu': True,
        }
    }
}

FFMPEG_CMD = 'ffmpeg -i "%(infile)s" -vcodec copy -acodec copy "%(outfile)s"'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

        self.cmd = FFMPEG_CMD
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

        if 'video/x-flv' not in [e.mime_type for e in episodes if e.file_exists()]:
            return None

        return [(self.container.metadata.title, self._convert_episodes)]

    def _convert_episode(self, episode):
        retvalue = self._run_conversion(episode)

        if retvalue == 0:
            logger.info('FLV conversion successful.')
            self.rename_episode_file(episode, basename+'.mp4')
            os.remove(filename)
        else:
            logger.info('Error converting file. FFMPEG installed?')
            try:
                os.remove(target)
            except OSError:
                pass

    def _run_conversion(self, episode):
        if not youtube.is_video_link(episode.url):
            logger.debug('Not a YouTube video. Ignoring.')
            return

        filename = episode.local_filename(create=False)
        dirname = os.path.dirname(filename)
        basename, ext = os.path.splitext(os.path.basename(filename))

        if open(filename, 'rb').read(3) != 'FLV':
            logger.debug('Not a FLV file. Ignoring.')
            return

        if ext == '.mp4':
            # Move file out of place for conversion
            newname = os.path.join(dirname, basename+'.flv')
            os.rename(filename, newname)
            filename = newname

        target = os.path.join(dirname, basename+'.mp4')
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
