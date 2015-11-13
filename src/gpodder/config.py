# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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
from gpodder import jsonconfig

import atexit
import os
import shutil
import time
import logging

_ = gpodder.gettext

defaults = {
    # External applications used for playback
    'player': {
        'audio': 'default',
        'video': 'default',
    },

    # gpodder.net settings
    'mygpo': {
        'enabled': False,
        'server': 'gpodder.net',
        'username': '',
        'password': '',
        'device': {
            'uid': util.get_hostname(),
            'type': 'desktop',
            'caption': _('gPodder on %s') % util.get_hostname(),
        },
    },

    # Various limits (downloading, updating, etc..)
    'limit': {
        'bandwidth': {
            'enabled': False,
            'kbps': 500.0, # maximum kB/s per download
        },
        'downloads': {
            'enabled': True,
            'concurrent': 1,
        },
        'episodes': 200, # max episodes per feed
    },

    # Behavior of downloads
    'downloads': {
        'chronological_order': True, # download older episodes first
    },

    # Automatic feed updates, download removal and retry on download timeout
    'auto': {
        'update': {
            'enabled': False,
            'frequency': 20, # minutes
        },

        'cleanup': {
            'days': 7,
            'played': False,
            'unplayed': False,
            'unfinished': True,
        },

        'retries': 3, # number of retries when downloads time out
    },

    # Software updates from gpodder.org
    'software_update': {
        'check_on_startup': True, # check for updates on start
        'last_check': 0, # unix timestamp of last update check
        'interval': 5, # interval (in days) to check for updates
    },

    'ui': {
        # Settings for the Command-Line Interface
        'cli': {
            'colors': True,
        },

        # Settings for the QML UI (MeeGo Harmattan / N9)
        'qml': {
            'state': {
                'episode_list_filter': 0,
            },

            'autorotate': False,
        },

        # Settings for the Gtk UI
        'gtk': {
            'state': {
                'main_window': {
                    'width': 700,
                    'height': 500,
                    'x': -1, 'y': -1, 'maximized': False,

                    'paned_position': 200,
                    'episode_list_size': 200,
                },
                'episode_selector': {
                    'width': 600,
                    'height': 400,
                    'x': -1, 'y': -1, 'maximized': False,
                },
                'episode_window': {
                    'width': 500,
                    'height': 400,
                    'x': -1, 'y': -1, 'maximized': False,
                },
            },

            'toolbar': False,
            'html_shownotes': True,
            'new_episodes': 'show', # ignore, show, queue, download
            'live_search_delay': 200,

            'podcast_list': {
                'all_episodes': True,
                'sections': True,
                'view_mode': 1,
                'hide_empty': False,
            },

            'episode_list': {
                'descriptions': True,
                'view_mode': 1,
                'columns': int('110', 2), # bitfield of visible columns
            },

            'download_list': {
                'remove_finished': True,
            },
        },
    },

    # Synchronization with portable devices (MP3 players, etc..)
    'device_sync': {
        'device_type': 'none', # Possible values: 'none', 'filesystem', 'ipod'
        'device_folder': '/media',        

        'one_folder_per_podcast': True,
        'skip_played_episodes': True,
        'delete_played_episodes': False,

        'max_filename_length': 999,

        'custom_sync_name': '{episode.sortdate}_{episode.title}',
        'custom_sync_name_enabled': False,

        'after_sync': {
            'mark_episodes_played': False,
            'delete_episodes': False,
            'sync_disks': False,
        },
        'playlists': {
            'create': True,
            'two_way_sync': False,
            'use_absolute_path': True,
            'folder': 'Playlists',
        }

    },

    'youtube': {
        'preferred_fmt_id': 18, # default fmt_id (see fallbacks in youtube.py)
        'preferred_fmt_ids': [], # for advanced uses (custom fallback sequence)
        'api_key_v3': '', # API key, register for one at https://developers.google.com/youtube/v3/
    },

    'vimeo': {
        'fileformat': '720p', # preferred file format (see vimeo.py)
    },

    'extensions': {
        'enabled': [],
    },

    'flattr': {
        'token': '',
        'flattr_on_play': False,
    },
}

# The sooner this goes away, the better
gPodderSettings_LegacySupport = {
    'player': 'player.audio',
    'videoplayer': 'player.video',
    'limit_rate': 'limit.bandwidth.enabled',
    'limit_rate_value': 'limit.bandwidth.kbps',
    'max_downloads_enabled': 'limit.downloads.enabled',
    'max_downloads': 'limit.downloads.concurrent',
    'episode_old_age': 'auto.cleanup.days',
    'auto_remove_played_episodes': 'auto.cleanup.played',
    'auto_remove_unfinished_episodes': 'auto.cleanup.unfinished',
    'auto_remove_unplayed_episodes': 'auto.cleanup.unplayed',
    'max_episodes_per_feed': 'limit.episodes',
    'show_toolbar': 'ui.gtk.toolbar',
    'episode_list_descriptions': 'ui.gtk.episode_list.descriptions',
    'podcast_list_view_all': 'ui.gtk.podcast_list.all_episodes',
    'podcast_list_sections': 'ui.gtk.podcast_list.sections',
    'enable_html_shownotes': 'ui.gtk.html_shownotes',
    'episode_list_view_mode': 'ui.gtk.episode_list.view_mode',
    'podcast_list_view_mode': 'ui.gtk.podcast_list.view_mode',
    'podcast_list_hide_boring': 'ui.gtk.podcast_list.hide_empty',
    'episode_list_columns': 'ui.gtk.episode_list.columns',
    'auto_cleanup_downloads': 'ui.gtk.download_list.remove_finished',
    'auto_update_feeds': 'auto.update.enabled',
    'auto_update_frequency': 'auto.update.frequency',
    'auto_download': 'ui.gtk.new_episodes',
}

logger = logging.getLogger(__name__)


def config_value_to_string(config_value):
    config_type = type(config_value)

    if config_type == list:
        return ','.join(map(config_value_to_string, config_value))
    elif config_type in (str, unicode):
        return config_value
    else:
        return str(config_value)

def string_to_config_value(new_value, old_value):
    config_type = type(old_value)

    if config_type == list:
        return filter(None, [x.strip() for x in new_value.split(',')])
    elif config_type == bool:
        return (new_value.strip().lower() in ('1', 'true'))
    else:
        return config_type(new_value)


class Config(object):
    # Number of seconds after which settings are auto-saved
    WRITE_TO_DISK_TIMEOUT = 60

    def __init__(self, filename='gpodder.json'):
        self.__json_config = jsonconfig.JsonConfig(default=defaults,
                on_key_changed=self._on_key_changed)
        self.__save_thread = None
        self.__filename = filename
        self.__observers = []

        self.load()

        # If there is no configuration file, we create one here (bug 1511)
        if not os.path.exists(self.__filename):
            self.save()

        atexit.register(self.__atexit)

    def register_defaults(self, defaults):
        """
        Register default configuration options (e.g. for extensions)

        This function takes a dictionary that will be merged into the
        current configuration if the keys don't yet exist. This can
        be used to add a default configuration for extension modules.
        """
        self.__json_config._merge_keys(defaults)

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
            logger.warn('Observer already added: %s', repr(callback))

    def remove_observer(self, callback):
        """
        Remove an observer previously added to this object.
        """
        if callback in self.__observers:
            self.__observers.remove(callback)
        else:
            logger.warn('Observer not added: %s', repr(callback))

    def all_keys(self):
        return self.__json_config._keys_iter()

    def schedule_save(self):
        if self.__save_thread is None:
            self.__save_thread = util.run_in_background(self.save_thread_proc, True)

    def save_thread_proc(self):
        time.sleep(self.WRITE_TO_DISK_TIMEOUT)
        if self.__save_thread is not None:
            self.save()

    def __atexit(self):
        if self.__save_thread is not None:
            self.save()

    def save(self, filename=None):
        if filename is None:
            filename = self.__filename

        logger.info('Flushing settings to disk')

        try:
            fp = open(filename+'.tmp', 'wt')
            fp.write(repr(self.__json_config))
            fp.close()
            util.atomic_rename(filename+'.tmp', filename)
        except:
            logger.error('Cannot write settings to %s', filename)
            util.delete_file(filename+'.tmp')
            raise

        self.__save_thread = None

    def load(self, filename=None):
        if filename is not None:
            self.__filename = filename

        if os.path.exists(self.__filename):
            try:
                data = open(self.__filename, 'rt').read()
                new_keys_added = self.__json_config._restore(data)
            except:
                logger.warn('Cannot parse config file: %s',
                        self.__filename, exc_info=True)
                new_keys_added = False

            if new_keys_added:
                logger.info('New default keys added - saving config.')
                self.save()

    def toggle_flag(self, name):
        setattr(self, name, not getattr(self, name))

    def update_field(self, name, new_value):
        """Update a config field, converting strings to the right types"""
        old_value = self._lookup(name)
        new_value = string_to_config_value(new_value, old_value)
        setattr(self, name, new_value)
        return True

    def _on_key_changed(self, name, old_value, value):
        if 'ui.gtk.state' not in name:
            # Only log non-UI state changes
            logger.debug('%s: %s -> %s', name, old_value, value)
        for observer in self.__observers:
            try:
                observer(name, old_value, value)
            except Exception, exception:
                logger.error('Error while calling observer %r: %s',
                        observer, exception, exc_info=True)

        self.schedule_save()

    def __getattr__(self, name):
        if name in gPodderSettings_LegacySupport:
            name = gPodderSettings_LegacySupport[name]

        return getattr(self.__json_config, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        if name in gPodderSettings_LegacySupport:
            name = gPodderSettings_LegacySupport[name]

        setattr(self.__json_config, name, value)

