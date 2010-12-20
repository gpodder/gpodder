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
    'audio_played_dbus': False,
    'auto_cleanup_downloads': True,
    'auto_download': 'never',
    'auto_remove_played_episodes': False,
    'auto_remove_unplayed_episodes': False,
    'auto_update_feeds': False,
    'auto_update_frequency': 20,
    'custom_player_copy_coverart': False,
    'custom_player_coverart_format': 'JPEG',
    'custom_player_coverart_name': 'folder.jpg',
    'custom_player_coverart_size': 176,
    'custom_sync_name': '{episode.basename}',
    'custom_sync_name_enabled': True,
    'device_type': 'none',
    'disable_pre_sync_conversion': False,
    'display_tray_icon': False,
    'do_not_show_new_episodes_dialog': False,
    'double_click_episode_action': 'shownotes',
    'download_dir': default_download_dir,
    'enable_html_shownotes': True,
    'enable_notifications': True,
    'episode_list_descriptions': True,
    'episode_list_view_mode': 1,
    'episode_old_age': 7,
    'fssync_channel_subfolders': True,
    'ipod_delete_played_from_db': False,
    'ipod_mount': '/media/ipod',
    'ipod_purge_old_episodes': False,
    'ipod_write_gtkpod_extended': False,
    'limit_rate': False,
    'limit_rate_value': 500.0,
    'max_downloads': 1,
    'max_downloads_enabled': True,
    'max_episodes_per_feed': 200,
    'mimetype_prefs': '',
    'minimize_to_tray': False,
    'mp3_player_delete_played': False,
    'mp3_player_folder': '/media/usbdisk',
    'mp3_player_max_filename_length': 100,
    'mp3_player_playlist_absolute_path': True,
    'mp3_player_playlist_file': 'PLAYLISTS/gpodder.m3u',
    'mp3_player_playlist_win_path': True,
    'mp3_player_use_scrobbler_log': False,
    'mtp_audio_folder': '',
    'mtp_image_folder': '',
    'mtp_podcast_folders': False,
    'mtp_video_folder': '',
    'mygpo_device_caption': _('gPodder on %s') % util.get_hostname(),
    'mygpo_device_type': 'desktop',
    'mygpo_device_uid': util.get_hostname(),
    'mygpo_enabled': False,
    'mygpo_password': '',
    'mygpo_server': 'gpodder.net',
    'mygpo_username': '',
    'on_sync_delete': False,
    'on_sync_mark_played': False,
    'only_sync_not_played': False,
    'opml_url': 'http://gpodder.org/directory.opml',
    'paned_position': 200,
    'player': 'default',
    'podcast_list_hide_boring': False,
    'podcast_list_view_all': True,
    'podcast_list_view_mode': 1,
    'rockbox_copy_coverart': False,
    'rockbox_coverart_size': 100,
    'rotation_mode': 0,
    'show_toolbar': True,
    'sync_disks_after_transfer': True,
    'toplist_url': 'http://gpodder.org/toplist.opml',
    'update_on_startup': False,
    'video_played_dbus': False,
    'videoplayer': 'default',
    'youtube_preferred_fmt_id': 18,
}


# Helper function to add window-specific properties (position and size)
def window_props(config_prefix, x=-1, y=-1, width=700, height=500):
    return {
            config_prefix+'_x': x,
            config_prefix+'_y': y,
            config_prefix+'_width': width,
            config_prefix+'_height': height,
            config_prefix+'_maximized': False,
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

        for key, default in self.Settings.items():
            fieldtype = type(default)
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

        for key, default in self.Settings.items():
            fieldtype = type(default)
            value = default
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
            default = self.Settings[name]
            fieldtype = type(default)
            if fieldtype == bool:
                setattr(self, name, not getattr(self, name))
            else:
                log('Cannot toggle value: %s (not boolean)', name, sender=self)
        else:
            log('Invalid setting name: %s', name, sender=self)

    def update_field(self, name, new_value):
        if name in self.Settings:
            default = self.Settings[name]
            fieldtype = type(default)
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
            default = self.Settings[name]
            fieldtype = type(default)
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

