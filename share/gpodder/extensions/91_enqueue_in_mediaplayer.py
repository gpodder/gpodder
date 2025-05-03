# -*- coding: utf-8 -*-
# Extension script to add a context menu item for enqueueing episodes in a player
# Requirements: gPodder 3.x (or "tres" branch newer than 2011-06-08)
# (c) 2011-06-08 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.
import functools
import logging
import pathlib
import urllib.parse

import gi  # isort:skip
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Enqueue/Resume in media players')
__description__ = _('Add a context menu item for enqueueing/resuming playback of episodes in installed media players')
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'https://gpodder.github.io/docs/extensions/enqueueinmediaplayer.html'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__category__ = 'interface'
__only_for__ = 'gtk'


DefaultConfig = {
    'enqueue_after_download': False,  # Set to True to enqueue an episode right after downloading
    'default_player': '',  # Set to the player to be used for auto-enqueueing (otherwise pick first installed)
}


class Player(object):
    def __init__(self, slug, application, command):
        self.slug = slug
        self.application = application
        self.title = '/'.join((_('Enqueue in'), application))
        self.command = command
        self.gpodder = None

    def is_installed(self):
        raise NotImplementedError('Must be implemented by subclass')

    def open_files(self, filenames):
        raise NotImplementedError('Must be implemented by subclass')

    def enqueue_episodes(self, episodes, config=None):
        filenames = [episode.get_playback_url(config=config) for episode in episodes]

        self.open_files(filenames)

        for episode in episodes:
            episode.playback_mark()
            if self.gpodder is not None:
                self.gpodder.update_episode_list_icons(selected=True)


class FreeDesktopPlayer(Player):
    def is_installed(self):
        return util.find_command(self.command[0]) is not None

    def open_files(self, filenames):
        util.Popen(self.command + filenames)


class Win32Player(Player):
    def is_installed(self):
        if not gpodder.ui.win32:
            return False

        from gpodder.gtkui.desktopfile import win32_read_registry_key
        try:
            self.command = win32_read_registry_key(self.command)
            return True
        except Exception as e:
            logger.warning('Win32 player not found: %s (%s)', self.command, e)

        return False

    def open_files(self, filenames):
        for cmd in util.format_desktop_command(self.command, filenames):
            util.Popen(cmd, close_fds=True)


class MPRISResumer(FreeDesktopPlayer):
    """Resume episode playback at saved time."""

    OBJECT_PLAYER = '/org/mpris/MediaPlayer2'
    OBJECT_DBUS = '/org/freedesktop/DBus'
    INTERFACE_PLAYER = 'org.mpris.MediaPlayer2.Player'
    INTERFACE_PROPS = 'org.freedesktop.DBus.Properties'
    SIGNAL_PROP_CHANGE = 'PropertiesChanged'
    NAME_DBUS = 'org.freedesktop.DBus'

    def __init__(self, slug, application, command, bus_name):
        super(MPRISResumer, self).__init__(slug, application, command)
        self.title = '/'.join((_('Resume in'), application))
        self.bus_name = bus_name
        self.player = None
        self.position_us = None
        self.url = None
        self.watcher_id = None

    def is_installed(self):
        if gpodder.ui.win32:
            return False
        return util.find_command(self.command[0]) is not None

    def resume_episode(self, episodes, config=None):
        """Resume playback of the first episode in given episodes."""
        self.position_us = episodes[0].current_position * 1e6
        self.url = episodes[0].get_playback_url(config=config)
        if self.url.startswith('/'):
            self.url = pathlib.Path(self.url).as_uri()

        if self.player is None:
            self._start_and_resume()
        else:
            self._open_and_set_pos()

        episodes[0].playback_mark()
        if self.gpodder is not None:
            self.gpodder.update_episode_list_icons(selected=True)

    def _start_and_resume(self):
        self.watcher_id = Gio.bus_watch_name(
            Gio.BusType.SESSION, self.bus_name,
            Gio.BusNameWatcherFlags.NONE,
            self.on_name_appeared, self.on_name_vanished)

    def on_name_appeared(self, connection, name, name_owner):
        if name == self.bus_name:
            logger.debug('MPRISResumer player %s is on the bus', name)
            self.player = Gio.DBusProxy.new_sync(
                connection, Gio.DBusProxyFlags.NONE, None,
                name, self.OBJECT_PLAYER, self.INTERFACE_PLAYER,
                None)
            if self.player is None:
                logger.error('Failed to create player proxy for %s', name)
                return
            self._open_and_set_pos()

    def on_name_vanished(self, connection, name):
        if name == self.bus_name:
            if self.player is None:
                logger.debug('MPRISResumer player %s not found on the bus, starting...', name)
                super(MPRISResumer, self).open_files([])
            else:
                logger.debug('MPRISResumer player %s vanished', name)
                self.player = None
                if self.watcher_id is not None:
                    Gio.bus_unwatch_name(self.watcher_id)
                    self.watcher_id = None

    def _open_and_set_pos(self):
        if self.player is None:
            logger.debug('Proxy for player %s does not exist', self.bus_name)
            return

        self.player.connect('g-properties-changed', self.on_props_changed)
        logger.debug('Opening %s', self.url)
        self.player.OpenUri('(s)', self.url)

    def on_props_changed(self, proxy, changed_props, invalidated_props):
        props = changed_props.unpack()
        metadata = props.get('Metadata')
        if metadata is None:
            logger.debug('No metadata in changed properties')
            return

        url = metadata.get('xesam:url')
        track_id = metadata.get('mpris:trackid')
        if url is not None and track_id is not None:
            if (url == self.url  # Also test unquoted URLs because player bugs
                    or urllib.parse.unquote(url) == urllib.parse.unquote(self.url)):
                self.player.disconnect_by_func(self.on_props_changed)
                logger.debug('Setting %s, track %s position to %d',
                             url, track_id, self.position_us)
                self.player.SetPosition('(ox)', track_id, self.position_us)
                self.player.Play()
            else:
                logger.debug('Player has unexpected url: %s', url)


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

    # Strawberry, https://www.strawberrymusicplayer.org/
    FreeDesktopPlayer('strawberry', 'Strawberry', ['strawberry', '--append']),

    # Parole, http://docs.xfce.org/apps/parole/start
    FreeDesktopPlayer('parole', 'Parole', ['parole', '-a']),

    # Winamp 2.x, http://www.oldversion.com/windows/winamp/
    Win32Player('winamp', 'Winamp', r'HKEY_CLASSES_ROOT\Winamp.File\shell\Enqueue\command'),

    # VLC media player, http://videolan.org/vlc/
    Win32Player('vlc', 'VLC', r'HKEY_CLASSES_ROOT\VLC.mp3\shell\AddToPlaylistVLC\command'),

    # SMPlayer, https://www.smplayer.info (unsigned installer: SMPlayer from Windows store
    # doesn't create this but HKEY_CLASSES_ROOT\AppX055xaggmfvyyr7t0hd5am4em22jvax6z\Shell\enqueue
    # and other obscure app names)
    Win32Player('smplayer', 'SMPlayer', r'HKEY_CLASSES_ROOT\MPlayerFileVideo\shell\enqueue\command'),

    # foobar2000, http://www.foobar2000.org/
    Win32Player('foobar2000', 'foobar2000', r'HKEY_CLASSES_ROOT\foobar2000.MP3\shell\enqueue\command'),
]


RESUMERS = [
    # doesn't play on my system, but the track is appended.
    MPRISResumer('amarok', 'Amarok', ['amarok', '--play'], 'org.mpris.MediaPlayer2.amarok'),

    MPRISResumer('vlc', 'VLC', ['vlc', '--started-from-file'], 'org.mpris.MediaPlayer2.vlc'),

    # totem mpris2 plugin is broken for me: it raises AttributeError:
    #  File "/usr/lib/totem/plugins/dbus/dbusservice.py", line 329, in OpenUri
    #       self.totem.add_to_playlist_and_play (uri)
    # MPRISResumer('totem', 'Totem', ['totem'], 'org.mpris.MediaPlayer2.totem'),

    # with https://github.com/Serranya/deadbeef-mpris2-plugin
    MPRISResumer('deadbeef', 'DeaDBeeF', ['deadbeef'], 'org.mpris.MediaPlayer2.DeaDBeeF'),

    # the gPodder Downloads directory must be in gmusicbrowser's library
    MPRISResumer('gmusicbrowser', 'gmusicbrowser', ['gmusicbrowser'], 'org.mpris.MediaPlayer2.gmusicbrowser'),

    # Audacious doesn't implement MPRIS2.OpenUri
    # MPRISResumer('audacious', 'resume in Audacious', ['audacious', '--enqueue'], 'org.mpris.MediaPlayer2.audacious'),

    # beware: clementine never exits on my system (even when launched from cmdline)
    # so the zombie clementine process will get all the bus messages and never answer
    # resulting in freezes and timeouts!
    MPRISResumer('clementine', 'Clementine', ['clementine'], 'org.mpris.MediaPlayer2.clementine'),

    # just enable the plugin
    MPRISResumer('parole', 'Parole', ['parole'], 'org.mpris.MediaPlayer2.parole'),

    # Needs the mpv-mpris plugin.
    MPRISResumer('mpv', 'mpv', ['mpv', '--player-operation-mode=pseudo-gui'], 'org.mpris.MediaPlayer2.mpv'),
]


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = container.config
        self.gpodder_config = self.container.manager.core.config

        # Only display media players that can be found at extension load time
        self.players = [player for player in PLAYERS if player.is_installed()]
        self.resumers = [r for r in RESUMERS if r.is_installed()]

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            for p in self.players + self.resumers:
                p.gpodder = ui_object

    def on_episodes_context_menu(self, episodes):
        if not any(e.file_exists() for e in episodes):
            return None

        ret = [(p.title, functools.partial(p.enqueue_episodes, config=self.gpodder_config))
               for p in self.players]

        # needs dbus, doesn't handle more than 1 episode
        # and no point in using DBus when episode is not played.
        # TODO: Detect Dbus availability with GDBus
        if not hasattr(gpodder.dbus_session_bus, 'fake') and \
                len(episodes) == 1 and episodes[0].current_position > 0:
            ret.extend([(p.title, functools.partial(p.resume_episode, config=self.gpodder_config))
                        for p in self.resumers])

        return ret

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
