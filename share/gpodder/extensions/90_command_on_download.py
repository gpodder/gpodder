# -*- coding: utf-8 -*-
#
# gPodder extension for running a command on successful episode download
#

import logging
import os

import gpodder
from gpodder import util

import gi  # isort:skip
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

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
            'playlist_title': episode.playlist_title(),
            'podcast': episode.channel.title,
            'published': episode.published_formatted('%Y-%m-%d %H:%M', '0000-00-00 00:00'),
            'section': episode.channel.section,
            'title': episode.title,
        }
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

    def on_cmd_changed(self, widget):
        self.container.config.command = widget.get_text()

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.cmd = Gtk.Entry()
        self.container.cmd.set_text(self.container.config.command)
        self.container.cmd.connect("changed", self.on_cmd_changed)
        self.container.cmd.set_halign(Gtk.Align.FILL)
        self.container.cmd_label = Gtk.Label(_('Command: '))
        self.container.hbox_cmd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_cmd.pack_start(self.container.cmd_label, False, False, 0)
        self.container.hbox_cmd.pack_start(self.container.cmd, True, True, 0)
        box.pack_start(self.container.hbox_cmd, False, False, 0)

        box.show_all()
        return box

    def on_preferences(self):
        return [(_('CmdOnDwnld'), self.show_preferences, self.container)]
