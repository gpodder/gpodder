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
import time
import threading
import ConfigParser
import logging

_ = gpodder.gettext

gPodderSettings = {
    # External applications used for playback
    'player': 'default',
    'videoplayer': 'default',

    # gpodder.net settings
    'mygpo_enabled': False,
    'mygpo_server': 'gpodder.net',
    'mygpo_username': '',
    'mygpo_password': '',
    'mygpo_device_uid': util.get_hostname(),
    'mygpo_device_type': 'desktop',
    'mygpo_device_caption': _('gPodder on %s') % util.get_hostname(),

    # Download options
    'limit_rate': False,
    'limit_rate_value': 500.0,
    'max_downloads_enabled': True,
    'max_downloads': 1,

    # Automatic removal of downloads
    'episode_old_age': 7,
    'auto_remove_played_episodes': False,
    'auto_remove_unfinished_episodes': True,
    'auto_remove_unplayed_episodes': False,

    # Periodic check for new episodes
    'auto_update_feeds': False,
    'auto_update_frequency': 20,

    # Limits
    'max_episodes_per_feed': 200,

    # View settings
    'show_toolbar': True,
    'episode_list_descriptions': True,
    'podcast_list_view_all': True,
    'podcast_list_sections': True,
    'enable_html_shownotes': True,
    'enable_notifications': True,

    # Display list filter configuration
    'episode_list_view_mode': 1,
    'episode_list_columns': int('101', 2), # bitfield of visible columns
    'podcast_list_view_mode': 1,
    'podcast_list_hide_boring': False,

    # URLs to OPML files
    'example_opml': 'http://gpodder.org/directory.opml',
    'toplist_opml': 'http://gpodder.org/toplist.opml',

    # YouTube
    'youtube_preferred_fmt_id': 18,

    # Misc
    '_paned_position': 200,
    'rotation_mode': 0,
    'mimetype_prefs': '',
    'auto_cleanup_downloads': True,
    'do_not_show_new_episodes_dialog': False,
    'auto_download': 'never',
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
gPodderSettings.update(window_props('_main_window', width=700, height=500))
gPodderSettings.update(window_props('_episode_selector', width=600, height=400))
gPodderSettings.update(window_props('_episode_window', width=500, height=400))

logger = logging.getLogger(__name__)

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

        # If there is no configuration file, we create one here (bug 1511)
        if not os.path.exists(self.__filename):
            self.save()

        atexit.register( self.__atexit)

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

        logger.info('Flushing settings to disk')

        parser = ConfigParser.RawConfigParser()
        parser.add_section(self.__section)

        for key, default in self.Settings.items():
            fieldtype = type(default)
            parser.set(self.__section, key, getattr(self, key, default))

        try:
            parser.write(open(filename, 'w'))
        except:
            logger.error('Cannot write settings to %s', filename)
            raise

        self.__save_thread = None

    def load(self, filename=None):
        if filename is not None:
            self.__filename = filename

        parser = ConfigParser.RawConfigParser()

        if os.path.exists(self.__filename):
            try:
                parser.read(self.__filename)
            except:
                logger.warn('Cannot parse config file: %s',
                        self.__filename, exc_info=True)

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
            except ConfigParser.NoOptionError:
                # Not (yet) set in the file, use the default value
                value = default
            except:
                logger.warn('Invalid value in %s for %s: %s',
                        self.__filename, key, value, exc_info=True)
                value = default

            self[key] = value

    def toggle_flag(self, name):
        if name in self.Settings:
            default = self.Settings[name]
            fieldtype = type(default)
            if fieldtype == bool:
                setattr(self, name, not getattr(self, name))
            else:
                logger.warn('Cannot toggle value: %s (not boolean)', name)
        else:
            logger.warn('Invalid setting name: %s', name)

    def update_field(self, name, new_value):
        if name in self.Settings:
            default = self.Settings[name]
            fieldtype = type(default)
            try:
                new_value = fieldtype(new_value)
            except:
                logger.warn('Cannot convert %s to %s.', str(new_value),
                        fieldtype.__name__, exc_info=True)
                return False
            setattr(self, name, new_value)
            return True
        else:
            logger.info('Ignoring invalid setting: %s', name)
            return False

    def __setattr__(self, name, value):
        if name in self.Settings:
            default = self.Settings[name]
            fieldtype = type(default)
            try:
                if self[name] != fieldtype(value):
                    old_value = self[name]
                    logger.info('Update %s: %s => %s', name, old_value, value)
                    self[name] = fieldtype(value)
                    for observer in self.__observers:
                        try:
                            # Notify observer about config change
                            observer(name, old_value, self[name])
                        except:
                            logger.error('Error while calling observer: %s',
                                    repr(observer), exc_info=True)
                    self.schedule_save()
            except:
                raise ValueError('%s has to be of type %s' % (name, fieldtype.__name__))
        else:
            object.__setattr__(self, name, value)

