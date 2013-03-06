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
    def __init__(self, command, title):
        self.command=command
        self.title=title
        self.gpodder=None

    def check_mediaplayer(self):
        return not (util.find_command(self.command[0]) == None)

    def enqueue_episodes(self, episodes):
        filenames = [episode.get_playback_url() for episode in episodes]

        play = subprocess.Popen(self.command + filenames,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        for episode in episodes:
            episode.playback_mark()
            self.gpodder.update_episode_list_icons(selected=True)


AMAROK=Player(['amarok', '--play', '--append'],
    ('%s/%s' % (_('Enqueue in'), 'Amarok')))
VLC=Player(['vlc', '--started-from-file', '--playlist-enqueue'],
    ('%s/%s' % (_('Enqueue in'), 'VLC')))
TOTEM=Player(['totem', '--enqueue'],
    ('%s/%s' % (_('Enqueue in'), 'Totem')))

class gPodderExtension:
    def __init__(self, container):
        self.container = container

        # Check media players
        self.players = list(p for p in [AMAROK, VLC, TOTEM] if p.check_mediaplayer())

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            for p in self.players:
                p.gpodder = ui_object


    def on_episodes_context_menu(self, episodes):
        if not [e for e in episodes if e.file_exists()]:
            return None

        menu_entries = list((p.title,p.enqueue_episodes) for p in self.players)
        return menu_entries
