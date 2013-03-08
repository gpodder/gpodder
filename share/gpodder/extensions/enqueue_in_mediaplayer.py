# -*- coding: utf-8 -*-
# Extension script to add a context menu item for enqueueing episodes in a player
# Requirements: gPodder 3.x (or "tres" branch newer than 2011-06-08)
# (c) 2011-06-08 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Enqueue in media players')
__description__ = _('Add a context menu item for enqueueing episodes in installed media players')
__author__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__category__ = 'interface'
__only_for__ = 'gtk'

AMAROK = (['amarok', '--play', '--append'],
    '%s/%s' % (_('Enqueue in'), 'Amarok'))
VLC = (['vlc', '--started-from-file', '--playlist-enqueue'],
    '%s/%s' % (_('Enqueue in'), 'VLC'))


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.gpodder = None

        # Check media players
        self.amarok_available = self.check_mediaplayer(AMAROK[0][0])
        self.vlc_available = self.check_mediaplayer(VLC[0][0])

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def check_mediaplayer(self, cmd):
        return not (util.find_command(cmd) == None)

    def _enqueue_episodes_cmd(self, episodes, cmd):
        filenames = [episode.get_playback_url() for episode in episodes]

        vlc = subprocess.Popen(cmd + filenames,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for episode in episodes:
            episode.playback_mark()
            self.gpodder.update_episode_list_icons(selected=True)

    def enqueue_episodes_amarok(self, episodes):
        self._enqueue_episodes_cmd(episodes, AMAROK[0])

    def enqueue_episodes_vlc(self, episodes):
        self._enqueue_episodes_cmd(episodes, VLC[0])

    def on_episodes_context_menu(self, episodes):
        if not [e for e in episodes if e.file_exists()]:
            return None

        menu_entries = []

        if self.amarok_available:
            menu_entries.append((AMAROK[1], self.enqueue_episodes_amarok))

        if self.vlc_available:
            menu_entries.append((VLC[1], self.enqueue_episodes_vlc))

        return menu_entries
