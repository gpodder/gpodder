# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

import atexit
import os
import shutil
import time
import threading
import logging

import json
import copy

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

    # Automatic feed updates and download removal
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
    },

    'ui': {
        # Settings for the Gtk UI
        'gtk': {
            'state': {
                'main_window': {
                    'width': 700,
                    'height': 500,
                    'x': -1, 'y': -1, 'maximized': False,

                    'paned_position': 200,
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

            'toolbar': True,
            'notifications': True,
            'html_shownotes': True,
            'new_episodes': 'show', # ignore, show, queue, download

            'podcast_list': {
                'all_episodes': True,
                'sections': True,
                'view_mode': 1,
                'hide_empty': False,
            },

            'episode_list': {
                'descriptions': True,
                'view_mode': 1,
                'columns': int('101', 2), # bitfield of visible columns
            },

            'download_list': {
                'remove_finished': True,
            },
        },
    },

    'youtube': {
        'preferred_fmt_id': 18,
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
    'paned_position': 'ui.gtk.state.main_window.paned_position',
    'enable_notifications': 'ui.gtk.notifications',
    'episode_list_descriptions': 'ui.gtk.episode_list.descriptions',
    'podcast_list_view_all': 'ui.gtk.podcast_list.all_episodes',
    'podcast_list_sections': 'ui.gtk.podcast_list.sections',
    'enable_html_shownotes': 'ui.gtk.html_shownotes',
    'episode_list_view_mode': 'ui.gtk.episode_list.view_mode',
    'podcast_list_view_mode': 'ui.gtk.podcast_list.view_mode',
    'podcast_list_hide_boring': 'ui.gtk.podcast_list.hide_empty',
    'youtube_preferred_fmt_id': 'youtube.preferred_fmt_id',
    'episode_list_columns': 'ui.gtk.episode_list.columns',
    'auto_cleanup_downloads': 'ui.gtk.download_list.remove_finished',
    'auto_update_feeds': 'auto.update.enabled',
    'auto_update_frequency': 'auto.update.frequency',
    'auto_download': 'ui.gtk.new_episodes',
}

logger = logging.getLogger(__name__)

class JsonConfigSubtree(object):
    def __init__(self, parent, name):
        self._parent = parent
        self._name = name

    def __repr__(self):
        return '<Subtree %r of %r>' % (self._name, self._parent)

    def _attr(self, name):
        return '.'.join((self._name, name))

    def __getitem__(self, name):
        return self._parent._lookup(self._name).__getitem__(name)

    def __setitem__(self, name, value):
        self._parent._lookup(self._name).__setitem__(name, value)

    def __getattr__(self, name):
        if name == 'keys':
            # Kludge for using dict() on a JsonConfigSubtree
            return getattr(self._parent._lookup(self._name), name)

        return getattr(self._parent, self._attr(name))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._parent.__setattr__(self._attr(name), value)


class JsonConfig(object):
    _DEFAULT = defaults
    _INDENT = 2

    def __init__(self, data=None, on_key_changed=None):
        self._data = copy.deepcopy(self._DEFAULT)
        self._on_key_changed = on_key_changed
        if data is not None:
            self._data = json.loads(data)

    def _restore(self, backup):
        self._data = json.loads(backup)

        # Recurse into the data and add missing items from _DEFAULT
        work_queue = [(self._data, self._DEFAULT)]
        while work_queue:
            data, default = work_queue.pop()
            for key, value in default.iteritems():
                if key not in data:
                    # Copy defaults for missing key
                    data[key] = copy.deepcopy(value)
                elif isinstance(value, dict):
                    # Recurse into sub-dictionaries
                    work_queue.append((data[key], value))

    def __repr__(self):
        return json.dumps(self._data, indent=self._INDENT)

    def _lookup(self, name):
        return reduce(lambda d, k: d[k], name.split('.'), self._data)

    def __getattr__(self, name):
        try:
            value = self._lookup(name)
            if not isinstance(value, dict):
                return value
        except KeyError:
            pass

        return JsonConfigSubtree(self, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        attrs = name.split('.')
        target_dict = self._data

        while attrs:
            attr = attrs.pop(0)
            if not attrs:
                old_value = target_dict.get(attr, None)
                if old_value != value or attr not in target_dict:
                    target_dict[attr] = value
                    if self._on_key_changed is not None:
                        self._on_key_changed(name, old_value, value)
                break

            target = target_dict.get(attr, None)
            if target is None or not isinstance(target, dict):
                target_dict[attr] = target = {}
            target_dict = target


class Config(object):
    # Number of seconds after which settings are auto-saved
    WRITE_TO_DISK_TIMEOUT = 60

    def __init__(self, filename='gpodder.json'):
        self.__json_config = JsonConfig(on_key_changed=self._on_key_changed)
        self.__save_thread = None
        self.__filename = filename
        self.__observers = []

        self.load()

        # If there is no configuration file, we create one here (bug 1511)
        if not os.path.exists(self.__filename):
            self.save()

        atexit.register(self.__atexit)

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

    def save(self, filename=None):
        if filename is None:
            filename = self.__filename

        logger.info('Flushing settings to disk')

        try:
            fp = open(filename+'.tmp', 'wb')
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
                data = open(self.__filename, 'rb').read()
                self.__json_config._restore(data)
            except:
                logger.warn('Cannot parse config file: %s',
                        self.__filename, exc_info=True)

    def toggle_flag(self, name):
        setattr(self, name, not getattr(self, name))

    def update_field(self, name, new_value):
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

