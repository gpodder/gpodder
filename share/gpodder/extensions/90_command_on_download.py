# -*- coding: utf-8 -*-
#
# gPodder extension for running a command on successful episode download
#

import datetime
import logging
import os

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Run a Command on Download')
__description__ = _('Run a predefined external command upon download completion.')
__authors__ = 'Eric Le Lay <elelay@macports.org>'
__doc__ = 'https://gpodder.github.io/docs/extensions/commandondownload.html'
__category__ = 'post-download'
__only_for__ = 'gtk, cli'


DefaultConfig = {
    'command': "zenity --info --width=600 --text=\"file=$filename "
               "podcast=$podcast title=$title published=$published "
               "section=$section playlist_title=$playlist_title\""
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_episode_downloaded(self, episode):
        cmd_template = self.container.config.command
        info = self.read_episode_info(episode)
        if info is None:
            return

        self.run_command(cmd_template, info)

    def read_episode_info(self, episode):
        filename = episode.local_filename(create=False, check_only=True)
        if filename is None:
            logger.warning("%s: missing episode filename", __title__)
            return None
        info = {
            'filename': filename,
            'playlist_title': None,
            'podcast': None,
            'published': None,
            'section': None,
            'title': None,
        }

        info['podcast'] = episode.channel.title
        info['title'] = episode.title
        info['section'] = episode.channel.section

        published = datetime.datetime.fromtimestamp(episode.published)
        info['published'] = published.strftime('%Y-%m-%d %H:%M')
        info['playlist_title'] = episode.playlist_title()
        return info

    def run_command(self, command, info):
        env = os.environ.copy()
        env.update(info)

        proc = util.Popen(command, shell=True, env=env, close_fds=True)
        proc.wait()
        if proc.returncode == 0:
            logger.info("%s succeeded", command)
        else:
            logger.warning("%s run with exit code %i", command, proc.returncode)
