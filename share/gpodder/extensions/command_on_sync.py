# -*- coding: utf-8 -*-
#
# gPodder extension for running a command on successful synchronization of all episodes
#

import datetime
import logging
import os

import gpodder
from gpodder import util

import gi  # isort:skip
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

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

    def on_cmd_changed(self, widget):
        self.container.config.command = widget.get_text()

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        title = Gtk.Label(use_markup=True, label=_('<b><big>Command On Sync Complete Extension</big></b>'))
        title.set_halign(Gtk.Align.CENTER)
        box.add(title)

        whatisthis = Gtk.Label(use_markup=True, wrap=True, label=_(
            'This extension defines a command to run upon device sync completion.'
        ))
        whatisthis.set_property('xalign', 0.0)
        box.add(whatisthis)

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
        return [(_('CmdOnSync'), self.show_preferences)]
