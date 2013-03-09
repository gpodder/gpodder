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

class Player:
    def __init__(self, application, command):
        self.title = '/'.join((_('Enqueue in'), application))
        self.command = command
        self.gpodder = None

    def is_installed(self):
        return util.find_command(self.command[0]) is not None

    def enqueue_episodes(self, episodes):
        print 'enqueue_episodes called'
        filenames = [episode.get_playback_url() for episode in episodes]

        subprocess.Popen(self.command + filenames,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for episode in episodes:
            episode.playback_mark()
            self.gpodder.update_episode_list_icons(selected=True)


PLAYERS = [
    # Amarok, http://amarok.kde.org/
    Player('Amarok', ['amarok', '--play', '--append']),

    # VLC, http://videolan.org/
    Player('VLC', ['vlc', '--started-from-file', '--playlist-enqueue']),

    # Totem, https://live.gnome.org/Totem
    Player('Totem', ['totem', '--enqueue']),
]

class gPodderExtension:
    def __init__(self, container):
        self.container = container

        # Only display media players that can be found at extension load time
        self.players = filter(lambda player: player.is_installed(), PLAYERS)

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            for p in self.players:
                p.gpodder = ui_object

    def on_episodes_context_menu(self, episodes):
        if not any(e.file_exists() for e in episodes):
            return None

        return [(p.title, p.enqueue_episodes) for p in self.players]

