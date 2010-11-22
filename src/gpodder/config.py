# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  config.py -- gPodder Configuration Manager
#  Thomas Perl <thp@perli.net>   2007-11-02
#


import gpodder
from gpodder import util
from gpodder.liblogger import log

import atexit
import os
import time
import threading
import ConfigParser

_ = gpodder.gettext

if gpodder.ui.fremantle:
    default_download_dir = os.path.join(os.path.expanduser('~'), 'MyDocs/Podcasts')
elif gpodder.ui.diablo:
    default_download_dir = '/media/mmc2/gpodder'
else:
    default_download_dir = os.path.join(os.path.expanduser('~'), 'gpodder-downloads')

gPodderSettings = {
    # General settings
    'player': (str, 'default', 
      ("The default player for all media, if set to 'default' this will "
        "attempt to use xdg-open on linux or the built-in media player on maemo.")),
    'videoplayer': (str, 'default',
      ("The default player for video")),
    'opml_url': (str, 'http://gpodder.org/directory.opml',
      ("A URL pointing to an OPML file which can be used to bulk-add podcasts.")),
    'toplist_url': (str, 'http://gpodder.org/toplist.opml',
      ("A URL pointing to a gPodder web services top podcasts list")),
    'custom_sync_name': ( str, '{episode.basename}',
      ("The name used when copying a file to a FS-based device. Available "
        "options are: episode.basename, episode.title, episode.published")),
    'custom_sync_name_enabled': ( bool, True,
      ("Enables renaming files when transfered to an FS-based device with "
        "respect to the 'custom_sync_name'.")),
    'max_downloads': ( int, 1,
      ("The maximum number of simultaneous downloads allowed at a single "
        "time. Requires 'max_downloads_enabled'.")),
    'max_downloads_enabled': ( bool, True,
      ("The 'max_downloads' setting will only work if this is set to 'True'.")), 
    'limit_rate': ( bool, False,
      ("The 'limit_rate_value' setting will only work if this is set to 'True'.")),
    'limit_rate_value': ( float, 500.0,
      ("Set a global speed limit (in KB/s) when downloading files. "
        "Requires 'limit_rate'.")),
    'episode_old_age': ( int, 7,
      ("The number of days before an episode is considered old.")),

    # Boolean config flags
    'update_on_startup': ( bool, False,
      ("Update the feed cache on startup.")),
    'only_sync_not_played': ( bool, False,
      ("Only sync episodes to a device that have not been marked played in gPodder.")),
    'fssync_channel_subfolders': ( bool, True,
      ("Create a directory for every feed when syncing to an FS-based device "
        "instead of putting all the episodes in a single directory.")),
    'on_sync_mark_played': ( bool, False,
      ("After syncing an episode, mark it as played in gPodder.")),
    'on_sync_delete': ( bool, False,
      ("After syncing an episode, delete it from gPodder.")),
    'auto_remove_played_episodes': ( bool, False,
      ("Auto-remove old episodes that are played.")),
    'auto_remove_unplayed_episodes': ( bool, False,
      ("Auto-remove old episodes that are unplayed.")),
    'auto_update_feeds': (bool, False,
      ("Automatically update feeds when gPodder is minimized. "
        "See 'auto_update_frequency' and 'auto_download'.")),
    'auto_update_frequency': (int, 20,
      ("The frequency (in minutes) at which gPodder will update all feeds "
        "if 'auto_update_feeds' is enabled.")),
    'auto_cleanup_downloads': (bool, True,
      ('Automatically removed cancelled and finished downloads from the list')),
    'episode_list_descriptions': (bool, True,
      ("Display the episode's description under the episode title in the GUI.")),
    'episode_list_thumbnails': (bool, True,
      ("Display thumbnails of downloaded image-feed episodes in the list")),
    'show_toolbar': (bool, True,
      ("Show the toolbar in the GUI's main window.")),
    'ipod_purge_old_episodes': (bool, False,
      ("Remove episodes from an iPod device if they've been marked as played "
        "on the device and they have no rating set (the rating can be set on "
        "the device by the user to prevent deletion).")),
    'ipod_delete_played_from_db': (bool, False,
      ("Remove episodes from gPodder if they've been marked as played "
        "on the device and they have no rating set (the rating can be set on "
        "the device by the user to prevent deletion).")),
    'ipod_write_gtkpod_extended': (bool, False,
      ("Write gtkpod extended database.")),
    'mp3_player_delete_played': (bool, False,
      ("Removes episodes from an FS-based device that have been marked as "
        "played in gPodder. Note: only works if 'only_sync_not_played' is "
        "also enabled.")),
    'disable_pre_sync_conversion': (bool, False,
      ("Disable pre-synchronization conversion of OGG files. This should be "
        "enabled for deviced that natively support OGG. Eg. Rockbox, iAudio")),
    
    # Tray icon and notification settings
    'display_tray_icon': (bool, False,
      ("Whether or not gPodder should display an icon in the system tray.")),
    'minimize_to_tray': (bool, False,
      ("If 'display_tray_icon' is enabled, when gPodder is minimized it will "
        "not be visible in the window list.")),  
    'start_iconified': (bool, False,
      ("When gPodder starts, send it to the tray immediately.")),
    'enable_notifications': (bool, True,
      ("Let gPodder use notification bubbles when it can completed certain "
        "tasks like downloading an episode or finishing syncing to a device.")),
    'auto_download': (str, 'never',
      ("Auto download episodes (never, minimized, always) - Fremantle also supports 'quiet'")),
    'do_not_show_new_episodes_dialog': (bool, False,
      ("Do not show the new episodes dialog after updating feed cache when "
        "gPodder is not minimized")),


    # Settings that are updated directly in code
    'ipod_mount': ( str, '/media/ipod',
      ("The moint point for an iPod Device.")),
    'mp3_player_folder': ( str, '/media/usbdisk',
      ("The moint point for an FS-based device.")),
    'device_type': ( str, 'none',
      ("The device type: 'mtp', 'filesystem' or 'ipod'")),
    'download_dir': (str, default_download_dir,
      ("The default directory that podcast episodes are downloaded to.")),

    # Playlist Management settings
    'mp3_player_playlist_file': (str, 'PLAYLISTS/gpodder.m3u',
      ("The relative path to where the playlist is stored on an FS-based device.")),
    'mp3_player_playlist_absolute_path': (bool, True,
      ("Whether or not the the playlist should contain relative or absolute "
        "paths; this is dependent on the player.")),
    'mp3_player_playlist_win_path': (bool, True,
      ("Whether or not the player requires Windows-style paths in the playlist.")),

    # Special settings (not in preferences)
    'on_quit_systray': (bool, False,
      ("When the 'X' button is clicked do not quit, send gPodder to the tray.")),
    'max_episodes_per_feed': (int, 200,
      ("The maximum number of episodes that gPodder will display in the episode "
        "list. Note: Set this to a lower value on slower hardware to speed up "
        "rendering of the episode list.")),
    'mp3_player_use_scrobbler_log': (bool, False,
      ("Attempt to use a Device's scrobbler.log to mark episodes as played in "
        "gPodder. Useful for Rockbox players.")),
    'mp3_player_max_filename_length': (int, 100,
      ("The maximum filename length for FS-based devices.")),
    'rockbox_copy_coverart' : (bool, False,
      ("Create rockbox-compatible coverart and copy it to the device when "
        "syncing. See: 'rockbox_coverart_size'.")),
    'rockbox_coverart_size' : (int, 100,
      ("The width of the coverart for the user's Rockbox player/skin.")),
    'custom_player_copy_coverart' : (bool, False,
      ("Create custom coverart for FS-based players.")),
    'custom_player_coverart_size' : (int, 176,
      ("The width of the coverart for the user's FS-based player.")),
    'custom_player_coverart_name' : (str, 'folder.jpg',
      ("The name of the coverart file accepted by the user's FS-based player.")),
    'custom_player_coverart_format' : (str, 'JPEG',
      ("The image format accepted by the user's FS-based player.")),
    'cmd_all_downloads_complete': (str, '',
      ("The path to a command that gets run after all downloads are completed.")),
    'cmd_download_complete': (str, '',
      ("The path to a command that gets run after a single download completes. "
        "See http://wiki.gpodder.org/wiki/Time_stretching for more info.")),
    'enable_html_shownotes': (bool, True,
      ("Allow HTML to be rendered in the episode information dialog.")),
    'maemo_enable_gestures': (bool, False,
      ("Enable fancy gestures on Maemo.")),
    'sync_disks_after_transfer': (bool, True,
      ("Call 'sync' after tranfering episodes to a device.")),
    'enable_fingerscroll': (bool, False,
      ("Enable the use of finger-scrollable widgets on Maemo.")),
    'double_click_episode_action': (str, 'shownotes',
      ("Episode double-click/enter action handler (shownotes, download, stream)")),
    'on_drag_mark_played': (bool, False,
      ("Mark episode as played when using drag'n'drop to copy/open it")),
    'open_torrent_after_download': (bool, False,
      ("Automatically open torrents after they have finished downloading")),

    'mtp_audio_folder': (str, '',
      ("The relative path to where audio podcasts are stored on an MTP device.")),
    'mtp_video_folder': (str, '',
      ("The relative path to where video podcasts are stored on an MTP device.")),
    'mtp_image_folder': (str, '',
      ("The relative path to where image podcasts are stored on an MTP device.")),
    'mtp_podcast_folders': (bool, False,
      ("Whether to create a folder per podcast on MTP devices.")),

    'allow_empty_feeds': (bool, True,
      ('Allow subscribing to feeds without episodes')),

    'episode_list_view_mode': (int, 1, # "Hide deleted episodes" (see gtkui/model.py)
      ('Internally used (current view mode)')),
    'podcast_list_view_mode': (int, 1, # Only on Fremantle
      ('Internally used (current view mode)')),
    'podcast_list_hide_boring': (bool, False,
      ('Hide podcasts in the main window for which the episode list is empty')),
    'podcast_list_view_all': (bool, True,
      ('Show an additional entry in the podcast list that contains all episodes')),

    'audio_played_dbus': (bool, False,
      ('Set to True if the audio player notifies gPodder about played episodes')),
    'video_played_dbus': (bool, False,
      ('Set to True if the video player notifies gPodder about played episodes')),

    'rotation_mode': (int, 0,
      ('Internally used on Maemo 5 for the current rotation mode')),

    'youtube_preferred_fmt_id': (int, 18,
      ('The preferred video format that should be downloaded from YouTube.')),

    # gpodder.net general settings
    'mygpo_username': (str, '',
      ("The user's gPodder web services username.")),
    'mygpo_password': (str, '',
      ("The user's gPodder web services password.")),
    'mygpo_enabled': (bool, False,
      ("Synchronize subscriptions with the web service.")),
    'mygpo_server': (str, 'gpodder.net',
      ('The hostname of the mygpo server in use.')),

    # gpodder.net device-specific settings
    'mygpo_device_uid': (str, util.get_hostname(),
      ("The UID that is assigned to this installation.")),
    'mygpo_device_caption': (str, _('gPodder on %s') % util.get_hostname(),
      ("The human-readable name of this installation.")),
    'mygpo_device_type': (str, 'desktop',
      ("The type of the device gPodder is running on.")),

    # Paned position
    'paned_position': ( int, 200,
      ("The width of the channel list.")),

    # Preferred mime types for podcasts with multiple content types
    'mimetype_prefs': (str, '',
      ("A comma-separated list of mimetypes, descending order of preference")),
}

# Helper function to add window-specific properties (position and size)
def window_props(config_prefix, x=-1, y=-1, width=700, height=500):
    return {
            config_prefix+'_x': (int, x),
            config_prefix+'_y': (int, y),
            config_prefix+'_width': (int, width),
            config_prefix+'_height': (int, height),
            config_prefix+'_maximized': (bool, False),
    }

# Register window-specific properties
gPodderSettings.update(window_props('main_window', width=700, height=500))
gPodderSettings.update(window_props('episode_selector', width=600, height=400))
gPodderSettings.update(window_props('episode_window', width=500, height=400))


class Config(dict):
    Settings = gPodderSettings
    
    # Number of seconds after which settings are auto-saved
    WRITE_TO_DISK_TIMEOUT = 60

    def __init__(self, filename='gpodder.conf'):
        dict.__init__(self)
        self.__save_thread = None
        self.__filename = filename
        self.__section = 'gpodder-conf-1'
        self.__observers = []

        self.load()
        self.apply_fixes()

        download_dir = os.environ.get('GPODDER_DOWNLOAD_DIR', None)
        if download_dir is not None:
            log('Setting download_dir from environment: %s', download_dir, sender=self)
            self.download_dir = download_dir

        atexit.register( self.__atexit)

    def apply_fixes(self):
        # Here you can add fixes in case syntax changes. These will be
        # applied whenever a configuration file is loaded.
        if '{channel' in self.custom_sync_name:
            log('Fixing OLD syntax {channel.*} => {podcast.*} in custom_sync_name.', sender=self)
            self.custom_sync_name = self.custom_sync_name.replace('{channel.', '{podcast.')
    
    def __getattr__(self, name):
        if name in self.Settings:
            return self[name]
        else:
            raise AttributeError('%s is not a setting' % name)

    def get_description(self, option_name):
        description = _('No description available.')
        
        if self.Settings.get(option_name) is not None:
            row = self.Settings[option_name]
            if len(row) >= 3:
                description = row[2]

        return description

    def add_observer(self, callback):
        """
        Add a callback function as observer. This callback
        will be called when a setting changes. It should 
        have this signature:

            observer(name, old_value, new_value)

        The "name" is the setting name, the "old_value" is
        the value that has been overwritten with "new_value".
        """
        if callback not in self.__observers:
            self.__observers.append(callback)
        else:
            log('Observer already added: %s', repr(callback), sender=self)

    def remove_observer(self, callback):
        """
        Remove an observer previously added to this object.
        """
        if callback in self.__observers:
            self.__observers.remove(callback)
        else:
            log('Observer not added :%s', repr(callback), sender=self)

    def schedule_save(self):
        if self.__save_thread is None:
            self.__save_thread = threading.Thread(target=self.save_thread_proc)
            self.__save_thread.setDaemon(True)
            self.__save_thread.start()

    def save_thread_proc(self):
        time.sleep(self.WRITE_TO_DISK_TIMEOUT)
        if self.__save_thread is not None:
            self.save()

    def __atexit(self):
        if self.__save_thread is not None:
            self.save()

    def get_backup(self):
        """Create a backup of the current settings

        Returns a dictionary with the current settings which can
        be used with "restore_backup" (see below) to restore the
        state of the configuration object at a future point in time.
        """
        return dict(self)

    def restore_backup(self, backup):
        """Restore a previously-created backup

        Restore a previously-created configuration backup (created
        with "get_backup" above) and notify any observer about the
        changed settings.
        """
        for key, value in backup.iteritems():
            setattr(self, key, value)

    def save(self, filename=None):
        if filename is None:
            filename = self.__filename

        log('Flushing settings to disk', sender=self)

        parser = ConfigParser.RawConfigParser()
        parser.add_section(self.__section)

        for key, value in self.Settings.items():
            fieldtype, default = value[:2]
            parser.set(self.__section, key, getattr(self, key, default))

        try:
            parser.write(open(filename, 'w'))
        except:
            log('Cannot write settings to %s', filename, sender=self)
            raise IOError('Cannot write to file: %s' % filename)

        self.__save_thread = None

    def load(self, filename=None):
        if filename is not None:
            self.__filename = filename

        parser = ConfigParser.RawConfigParser()

        if os.path.exists(self.__filename):
            try:
                parser.read(self.__filename)
            except:
                log('Cannot parse config file: %s', self.__filename,
                        sender=self, traceback=True)

        for key, value in self.Settings.items():
            fieldtype, default = value[:2]
            try:
                if not parser.has_section(self.__section):
                    value = default
                elif fieldtype == int:
                    value = parser.getint(self.__section, key)
                elif fieldtype == float:
                    value = parser.getfloat(self.__section, key)
                elif fieldtype == bool:
                    value = parser.getboolean(self.__section, key)
                else:
                    value = fieldtype(parser.get(self.__section, key))
            except:
                log('Invalid value in %s for %s: %s', self.__filename,
                        key, value, sender=self, traceback=True)
                value = default

            self[key] = value

    def toggle_flag(self, name):
        if name in self.Settings:
            (fieldtype, default) = self.Settings[name][:2]
            if fieldtype == bool:
                setattr(self, name, not getattr(self, name))
            else:
                log('Cannot toggle value: %s (not boolean)', name, sender=self)
        else:
            log('Invalid setting name: %s', name, sender=self)

    def update_field(self, name, new_value):
        if name in self.Settings:
            (fieldtype, default) = self.Settings[name][:2]
            try:
                new_value = fieldtype(new_value)
            except:
                log('Cannot convert "%s" to %s. Ignoring.', str(new_value), fieldtype.__name__, sender=self)
                return False
            setattr(self, name, new_value)
            return True
        else:
            log('Invalid setting name: %s', name, sender=self)
            return False

    def __setattr__(self, name, value):
        if name in self.Settings:
            fieldtype, default = self.Settings[name][:2]
            try:
                if self[name] != fieldtype(value):
                    old_value = self[name]
                    log('Update %s: %s => %s', name, old_value, value, sender=self)
                    self[name] = fieldtype(value)
                    for observer in self.__observers:
                        try:
                            # Notify observer about config change
                            observer(name, old_value, self[name])
                        except:
                            log('Error while calling observer: %s',
                                    repr(observer), sender=self,
                                    traceback=True)
                    self.schedule_save()
            except:
                raise ValueError('%s has to be of type %s' % (name, fieldtype.__name__))
        else:
            object.__setattr__(self, name, value)

