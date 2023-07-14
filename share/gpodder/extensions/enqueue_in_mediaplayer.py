# -*- coding: utf-8 -*-
# Extension script to add a context menu item for enqueueing episodes in a player
# Requirements: gPodder 3.x (or "tres" branch newer than 2011-06-08)
# (c) 2011-06-08 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.
import functools
import logging

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
        raise NotImplemented('Must be implemented by subclass')

    def open_files(self, filenames):
        raise NotImplemented('Must be implemented by subclass')

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
    """
    resume episod playback at saved time
    """
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

    def is_installed(self):
        if gpodder.ui.win32:
            return False
        return util.find_command(self.command[0]) is not None

    def enqueue_episodes(self, episodes, config=None):
        self.do_enqueue(episodes[0].get_playback_url(config=config),
                        episodes[0].current_position)

        for episode in episodes:
            episode.playback_mark()
            if self.gpodder is not None:
                self.gpodder.update_episode_list_icons(selected=True)

    def init_dbus(self):
        bus = gpodder.dbus_session_bus

        if not bus.name_has_owner(self.bus_name):
            logger.debug('MPRISResumer %s is not there...', self.bus_name)
            return False

        self.player = bus.get_object(self.bus_name, self.OBJECT_PLAYER)
        self.signal_match = self.player.connect_to_signal(self.SIGNAL_PROP_CHANGE,
            self.on_prop_change,
            dbus_interface=self.INTERFACE_PROPS)
        return True

    def enqueue_when_ready(self, filename, pos):
        def name_owner_changed(name, old_owner, new_owner):
            logger.debug('name_owner_changed "%s" "%s" "%s"',
                         name, old_owner, new_owner)
            if name == self.bus_name:
                logger.debug('MPRISResumer player %s is there', name)
                cancel.remove()
                util.idle_add(lambda: self.do_enqueue(filename, pos))

        bus = gpodder.dbus_session_bus
        obj = bus.get_object(self.NAME_DBUS, self.OBJECT_DBUS)
        cancel = obj.connect_to_signal('NameOwnerChanged', name_owner_changed, dbus_interface=self.NAME_DBUS)

    def do_enqueue(self, filename, pos):
        def on_reply():
            logger.debug('MPRISResumer opened %s', self.url)

        def on_error(exception):
            logger.error('MPRISResumer error %s', repr(exception))
            self.signal_match.remove()

        if filename.startswith('/'):
            try:
                import pathlib
                self.url = pathlib.Path(filename).as_uri()
            except ImportError:
                self.url = 'file://' + filename
        self.position_us = pos * 1000 * 1000  # pos in microseconds
        if self.init_dbus():
            # async to not freeze the ui waiting for the application to answer
            self.player.OpenUri(self.url,
                                dbus_interface=self.INTERFACE_PLAYER,
                                reply_handler=on_reply,
                                error_handler=on_error)
        else:
            self.enqueue_when_ready(filename, pos)
            logger.debug('MPRISResumer launching player %s', self.application)
            super(MPRISResumer, self).open_files([])

    def on_prop_change(self, interface, props, invalidated_props):
        def on_reply():
            pass

        def on_error(exception):
            logger.error('MPRISResumer SetPosition error %s', repr(exception))
            self.signal_match.remove()

        metadata = props.get('Metadata', {})
        url = metadata.get('xesam:url')
        track_id = metadata.get('mpris:trackid')
        if url is not None and track_id is not None:
            if url == self.url:
                logger.info('Enqueue %s setting track %s position=%d',
                            url, track_id, self.position_us)
                self.player.SetPosition(str(track_id), self.position_us,
                                        dbus_interface=self.INTERFACE_PLAYER,
                                        reply_handler=on_reply,
                                        error_handler=on_error)
            else:
                logger.debug('Changed but wrong url: %s, giving up', url)
            self.signal_match.remove()


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
    MPRISResumer('resume in deadbeef', 'DeaDBeeF', ['deadbeef'], 'org.mpris.MediaPlayer2.DeaDBeeF'),

    # the gPodder Downloads directory must be in gmusicbrowser's library
    MPRISResumer('resume in gmusicbrowser', 'gmusicbrowser', ['gmusicbrowser'], 'org.mpris.MediaPlayer2.gmusicbrowser'),

    # Audacious doesn't implement MPRIS2.OpenUri
    # MPRISResumer('audacious', 'resume in Audacious', ['audacious', '--enqueue'], 'org.mpris.MediaPlayer2.audacious'),

    # beware: clementine never exits on my system (even when launched from cmdline)
    # so the zombie clementine process will get all the bus messages and never answer
    # resulting in freezes and timeouts!
    MPRISResumer('clementine', 'Clementine', ['clementine'], 'org.mpris.MediaPlayer2.clementine'),

    # just enable the plugin
    MPRISResumer('parole', 'Parole', ['parole'], 'org.mpris.MediaPlayer2.parole'),
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
        if not hasattr(gpodder.dbus_session_bus, 'fake') and \
                len(episodes) == 1 and episodes[0].current_position > 0:
            ret.extend([(p.title, functools.partial(p.enqueue_episodes, config=self.gpodder_config))
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
