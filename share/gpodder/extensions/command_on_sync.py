# -*- coding: utf-8 -*-
#
# gPodder extension for running a command on successful synchronization of all episodes
#

import datetime
import logging
import os

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Run a Command on Sync')
__description__ = _('Run a custom external command upon sync completion.')
__authors__ = 'Eric Le Lay <elelay@macports.org>, Azer Abdullaev <azer.abdullaev.berlin+git@gmail.com>'
__doc__ = 'https://gpodder.github.io/docs/extensions/commandonsync.html'
__category__ = 'post-sync'
__only_for__ = 'gtk, cli'


DefaultConfig = {
    'command': 'zenity --info --width=600 --text="Sync completed!"',
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_all_episodes_synced(self):
        cmd_template = self.container.config.command
        self.run_command(cmd_template)

    def run_command(self, command):
        env = os.environ.copy()

        proc = util.Popen(command, shell=True, env=env, close_fds=True)
        proc.wait()
        if proc.returncode == 0:
            logger.info("Post-sync command %r succeeded", command)
        else:
            logger.warning("Post-sync command %r exited with status=%i", command, proc.returncode)
