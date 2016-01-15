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
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__category__ = 'interface'
__only_for__ = 'gtk'


DefaultConfig = {
    'enqueue_after_download': False, # Set to True to enqueue an episode right after downloading
    'default_player': '', # Set to the player to be used for auto-enqueueing (otherwise pick first installed)
}


class Player(object):
    def __init__(self, slug, application, command):
        self.slug = slug
        self.application = application
        self.title = '/'.join((_('Enqueue in'), application))
        self.command = command
        self.gpodder = None

    def is_installed(self):
        raise NotImplemented('Must be implemented by subclass')

    def open_files(self, filenames):
        raise NotImplemented('Must be implemented by subclass')

    def enqueue_episodes(self, episodes):
        filenames = [episode.get_playback_url() for episode in episodes]

        self.open_files(filenames)

        for episode in episodes:
            episode.playback_mark()
            if self.gpodder is not None:
                self.gpodder.update_episode_list_icons(selected=True)


class FreeDesktopPlayer(Player):
    def is_installed(self):
        return util.find_command(self.command[0]) is not None

    def open_files(self, filenames):
        subprocess.Popen(self.command + filenames,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class Win32Player(Player):
    def is_installed(self):
        if not gpodder.ui.win32:
            return False

        from gpodder.gtkui.desktopfile import win32_read_registry_key
        try:
            self.command = win32_read_registry_key(self.command)
            return True
        except Exception as e:
            logger.warn('Win32 player not found: %s (%s)', self.command, e)

        return False

    def open_files(self, filenames):
        for cmd in util.format_desktop_command(self.command, filenames):
            subprocess.Popen(cmd)


PLAYERS = [
    # Amarok, http://amarok.kde.org/
    FreeDesktopPlayer('amarok', 'Amarok', ['amarok', '--play', '--append']),

    # VLC, http://videolan.org/
    FreeDesktopPlayer('vlc', 'VLC', ['vlc', '--started-from-file', '--playlist-enqueue']),

    # Totem, https://live.gnome.org/Totem
    FreeDesktopPlayer('totem', 'Totem', ['totem', '--enqueue']),

    # DeaDBeeF, http://deadbeef.sourceforge.net/
    FreeDesktopPlayer('deadbeef', 'DeaDBeeF', ['deadbeef', '--queue']),

    # gmusicbrowser, http://gmusicbrowser.org/
    FreeDesktopPlayer('gmusicbrowser', 'gmusicbrowser', ['gmusicbrowser', '-enqueue']),

    # Audacious, http://audacious-media-player.org/
    FreeDesktopPlayer('audacious', 'Audacious', ['audacious', '--enqueue']),

    # Clementine, http://www.clementine-player.org/
    FreeDesktopPlayer('clementine', 'Clementine', ['clementine', '--append']),

    # Parole, http://docs.xfce.org/apps/parole/start
    FreeDesktopPlayer('parole', 'Parole', ['parole', '-a']),

    # Winamp 2.x, http://www.oldversion.com/windows/winamp/
    Win32Player('winamp', 'Winamp', r'HKEY_CLASSES_ROOT\Winamp.File\shell\Enqueue\command'),

    # VLC media player, http://videolan.org/vlc/
    Win32Player('vlc', 'VLC', r'HKEY_CLASSES_ROOT\VLC.mp3\shell\AddToPlaylistVLC\command'),

    # foobar2000, http://www.foobar2000.org/
    Win32Player('foobar2000', 'foobar2000', r'HKEY_CLASSES_ROOT\foobar2000.MP3\shell\enqueue\command'),
]

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = container.config

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

    def on_episode_downloaded(self, episode):
        if self.config.enqueue_after_download:
            if not self.config.default_player and len(self.players):
                player = self.players[0]
                logger.info('Picking first installed player: %s (%s)', player.slug, player.application)
            else:
                player = next((player for player in self.players if self.config.default_player == player.slug), None)
                if player is None:
                    logger.info('No player set, use one of: %r', [player.slug for player in self.players])
                    return

            logger.info('Enqueueing downloaded file in %s', player.application)
            player.enqueue_episodes([episode])
