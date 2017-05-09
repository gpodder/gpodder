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

__title__ = _('Enqueue in media player')
__description__ = _('Automatically enqueue downloaded podcasts')
__authors__ = 'boyska <piuttosto@logorroici.org>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__payment__ = ''
__category__ = 'post-download'
__only_for__ = 'gtk'


class Player(object):
    def __init__(self, application, command):
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
    FreeDesktopPlayer('Amarok', ['amarok', '--play', '--append']),

    # VLC, http://videolan.org/
    FreeDesktopPlayer('VLC', ['vlc', '--started-from-file', '--playlist-enqueue']),

    # Totem, https://live.gnome.org/Totem
    FreeDesktopPlayer('Totem', ['totem', '--enqueue']),

    # DeaDBeeF, http://deadbeef.sourceforge.net/
    FreeDesktopPlayer('DeaDBeeF', ['deadbeef', '--queue']),

    # gmusicbrowser, http://gmusicbrowser.org/
    FreeDesktopPlayer('gmusicbrowser', ['gmusicbrowser', '-enqueue']),

    # Audacious, http://audacious-media-player.org/
    FreeDesktopPlayer('Audacious', ['audacious', '--enqueue']),

    # Clementine, http://www.clementine-player.org/
    FreeDesktopPlayer('Clementine', ['clementine', '--append']),

    # Parole, http://docs.xfce.org/apps/parole/start
    FreeDesktopPlayer('Parole', ['parole', '-a']),

    # Winamp 2.x, http://www.oldversion.com/windows/winamp/
    Win32Player('Winamp', r'HKEY_CLASSES_ROOT\Winamp.File\shell\Enqueue\command'),

    # VLC media player, http://videolan.org/vlc/
    Win32Player('VLC', r'HKEY_CLASSES_ROOT\VLC.mp3\shell\AddToPlaylistVLC\command'),

    # foobar2000, http://www.foobar2000.org/
    Win32Player('foobar2000', r'HKEY_CLASSES_ROOT\foobar2000.MP3\shell\enqueue\command'),
]

DefaultConfig = {
    'default_player': ''
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = container.config

        # Only display media players that can be found at extension load time
        self.player = next(p for p in PLAYERS if p.is_installed())
        if self.config.default_player:  # further restricts
            try:
                self.player = next(p for p in PLAYERS
                                   if p.is_installed() and
                                   p.application == self.config.default_player)
            except StopIteration:  # no installed player matches name
                logger.warn('Invalid player "%s"' % self.config.default_player)
                logger.debug('Choose from %s' %
                             ','.join(p.application for p in PLAYERS))

    def on_episode_downloaded(self, episode):
        logger.debug('Enqueuing %s' % str(episode))
        self.player.enqueue_episodes([episode])
