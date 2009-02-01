# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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


import gtk
import pango

import gpodder
from gpodder import util
from gpodder.liblogger import log

import atexit
import os.path
import time
import threading
import ConfigParser

if gpodder.interface == gpodder.MAEMO:
    default_download_dir = '/media/mmc2/gpodder'
else:
    default_download_dir = os.path.expanduser('~/gpodder-downloads')

gPodderSettings = {
    # General settings
    'player': (str, 'default'),
    'videoplayer': (str, 'unspecified'),
    'opml_url': (str, 'http://gpodder.org/directory.opml'),
    'toplist_url': (str, 'http://gpodder.org/toplist.opml'),
    'http_proxy': ( str, '' ),
    'ftp_proxy': ( str, '' ),
    'custom_sync_name': ( str, '{episode.basename}' ),
    'custom_sync_name_enabled': ( bool, True ),
    'max_downloads': ( int, 3 ),
    'max_downloads_enabled': ( bool, False ), 
    'limit_rate': ( bool, False ),
    'limit_rate_value': ( float, 500.0 ),
    'episode_old_age': ( int, 7 ),

    # Boolean config flags
    'update_on_startup': ( bool, False ),
    'auto_download_when_minimized': (bool, False),
    'only_sync_not_played': ( bool, False ),
    'proxy_use_environment': ( bool, True ),
    'update_tags': ( bool, False ),
    'fssync_channel_subfolders': ( bool, True ),
    'on_sync_mark_played': ( bool, False ),
    'on_sync_delete': ( bool, False ),
    'auto_remove_old_episodes': ( bool, False ),
    'auto_update_feeds': (bool, False),
    'auto_update_frequency': (int, 20),
    'episode_list_descriptions': (bool, True),
    'show_toolbar': (bool, True),
    'ipod_write_gtkpod_extended': (bool, False),
    'ipod_purge_old_episodes': (bool, False),
    'mp3_player_delete_played': (bool, False),
    
    # Tray icon and notification settings
    'display_tray_icon': (bool, False),
    'minimize_to_tray': (bool, False),  
    'start_iconified': (bool, False),
    'enable_notifications': (bool, True),
    'on_quit_ask': (bool, True),

    # Bluetooth-related settings
    'bluetooth_use_device_address': (bool, False),
    'bluetooth_device_address': (str, '00:00:00:00:00:00'),
    'bluetooth_use_converter': (bool, False),
    'bluetooth_converter': (str, ''),

    # Settings that are updated directly in code
    'ipod_mount': ( str, '/media/ipod' ),
    'mp3_player_folder': ( str, '/media/usbdisk' ),
    'device_type': ( str, 'none' ),
    'download_dir': (str, default_download_dir),

    # Playlist Management settings
    'mp3_player_playlist_file': (str, 'PLAYLISTS/gpodder.m3u'),
    'mp3_player_playlist_absolute_path': (bool, False),
    'mp3_player_playlist_win_path': (bool, True),

    # Special settings (not in preferences)
    'default_new': ( int, 1 ),
    'use_si_units': ( bool, False ),
    'on_quit_systray': (bool, False),
    'create_m3u_playlists': (bool, False),
    'max_episodes_per_feed': (int, 200),
    'mp3_player_use_scrobbler_log': (bool, False),
    'mp3_player_max_filename_length': (int, 100),
    'show_url_entry_in_podcast_list': (bool, False),
    'maemo_allow_custom_player': (bool, False),
    'rockbox_copy_coverart' : (bool, False),
    'rockbox_coverart_size' : (int, 100),
    'custom_player_copy_coverart' : (bool, False),
    'custom_player_coverart_size' : (int, 176),
    'custom_player_coverart_name' : (str, 'folder.jpg'),
    'custom_player_coverart_format' : (str, 'JPEG'),
    'experimental_file_naming': (bool, False),
    'podcast_list_icon_size': (int, 32),
    'cmd_all_downloads_complete': (str, ''),
    'cmd_download_complete': (str, ''),
    'enable_streaming': (bool, False),
    'max_simulaneous_feeds_updating': (int, 3),
    'color_updating_feeds': (str, '#7db023'),
    'log_sqlite': (bool, False),

    # Hide the cover/pill from the podcast sidebar when it gets too small
    'podcast_sidebar_save_space': (bool, False),

    # Settings for my.gpodder.org
    'my_gpodder_username': (str, ''),
    'my_gpodder_password': (str, ''),
    'my_gpodder_autoupload': (bool, False),

    # Paned position
    'paned_position': ( int, 200 ),
}

# Helper function to add window-specific properties (position and size)
def window_props(config_prefix, x=100, y=100, width=700, height=500):
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

    def __init__( self, filename = 'gpodder.conf'):
        dict.__init__( self)
        self.__save_thread = None
        self.__filename = filename
        self.__section = 'gpodder-conf-1'
        self.__ignore_window_events = False
        self.__observers = []
        # Name, Type, Value, Type(python type), Editable?, Font style, Boolean?, Boolean value
        self.__model = gtk.ListStore(str, str, str, object, bool, int, bool, bool)

        atexit.register( self.__atexit)

        self.load()
    
    def __getattr__( self, name):
        if name in self.Settings:
            ( fieldtype, default ) = self.Settings[name]
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

    def connect_gtk_editable( self, name, editable):
        if name in self.Settings:
            editable.delete_text( 0, -1)
            editable.insert_text( str(getattr( self, name)))
            editable.connect( 'changed', lambda editable: setattr( self, name, editable.get_chars( 0, -1)))
        else:
            raise ValueError( '%s is not a setting' % name)

    def connect_gtk_spinbutton( self, name, spinbutton):
        if name in self.Settings:
            spinbutton.set_value( getattr( self, name))
            spinbutton.connect( 'value-changed', lambda spinbutton: setattr( self, name, spinbutton.get_value()))
        else:
            raise ValueError( '%s is not a setting' % name)

    def connect_gtk_paned( self, name, paned):
        if name in self.Settings:
            paned.set_position( getattr( self, name))
            paned_child = paned.get_child1()
            paned_child.connect( 'size-allocate', lambda x, y: setattr( self, name, paned.get_position()))
        else:
            raise ValueError( '%s is not a setting' % name)

    def connect_gtk_togglebutton( self, name, togglebutton):
        if name in self.Settings:
            togglebutton.set_active( getattr( self, name))
            togglebutton.connect( 'toggled', lambda togglebutton: setattr( self, name, togglebutton.get_active()))
        else:
            raise ValueError( '%s is not a setting' % name)
    
    def filechooser_selection_changed(self, name, filechooser):
        filename = filechooser.get_filename()
        if filename is not None:
            setattr(self, name, filename)

    def connect_gtk_filechooser(self, name, filechooser, is_for_files=False):
        if name in self.Settings:
            if is_for_files:
                # A FileChooser for a single file
                filechooser.set_filename(getattr(self, name))
            else:
                # A FileChooser for a folder
                filechooser.set_current_folder(getattr(self, name))
            filechooser.connect('selection-changed', lambda filechooser: self.filechooser_selection_changed(name, filechooser))
        else:
            raise ValueError('%s is not a setting'%name)

    def receive_configure_event( self, widget, event, config_prefix):
        (x, y, width, height, maximized) = map(lambda x: config_prefix + '_' + x, ['x', 'y', 'width', 'height', 'maximized'])
        ( x_pos, y_pos ) = widget.get_position()
        ( width_size, height_size ) = widget.get_size()
        if not self.__ignore_window_events and not (hasattr(self, maximized) and getattr(self, maximized)):
            setattr( self, x, x_pos)
            setattr( self, y, y_pos)
            setattr( self, width, width_size)
            setattr( self, height, height_size)

    def receive_window_state(self, widget, event, config_prefix):
        if hasattr(self, config_prefix+'_maximized'):
            setattr(self, config_prefix+'_maximized', bool(event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED))

    def enable_window_events(self):
        self.__ignore_window_events = False

    def disable_window_events(self):
        self.__ignore_window_events = True

    def connect_gtk_window( self, window, config_prefix, show_window=False):
        (x, y, width, height, maximized) = map(lambda x: config_prefix + '_' + x, ['x', 'y', 'width', 'height', 'maximized'])
        if set( ( x, y, width, height )).issubset( set( self.Settings)):
            window.resize( getattr( self, width), getattr( self, height))
            window.move( getattr( self, x), getattr( self, y))
            self.disable_window_events()
            util.idle_add(self.enable_window_events)
            window.connect('configure-event', self.receive_configure_event, config_prefix)
            window.connect('window-state-event', self.receive_window_state, config_prefix)
            if show_window:
                window.show()
            if hasattr(self, maximized) and getattr(self, maximized) == True:
                window.maximize()
        else:
            raise ValueError( 'Missing settings in set: %s' % ', '.join( ( x, y, width, height )))

    def schedule_save( self):
        if self.__save_thread is None:
            self.__save_thread = threading.Thread( target = self.save_thread_proc)
            self.__save_thread.start()

    def save_thread_proc( self):
        for i in range(self.WRITE_TO_DISK_TIMEOUT*10):
            if self.__save_thread is not None:
                time.sleep( .1)
        if self.__save_thread is not None:
            self.save()

    def __atexit( self):
        if self.__save_thread is not None:
            self.save()

    def save( self, filename = None):
        if filename is not None:
            self.__filename = filename

        log( 'Flushing settings to disk', sender = self)

        parser = ConfigParser.RawConfigParser()
        parser.add_section( self.__section)

        for ( key, ( fieldtype, default ) ) in self.Settings.items():
            parser.set( self.__section, key, getattr( self, key, default))

        try:
            parser.write( open( self.__filename, 'w'))
        except:
            raise IOError( 'Cannot write to file: %s' % self.__filename)

        self.__save_thread = None

    def load( self, filename = None):
        if filename is not None:
            self.__filename = filename

        self.__model.clear()

        parser = ConfigParser.RawConfigParser()
        try:
            parser.read( self.__filename)
        except:
            pass

        for key in sorted(self.Settings):
            (fieldtype, default) = self.Settings[key]
            try:
                if fieldtype == int:
                    value = parser.getint( self.__section, key)
                elif fieldtype == float:
                    value = parser.getfloat( self.__section, key)
                elif fieldtype == bool:
                    value = parser.getboolean( self.__section, key)
                else:
                    value = fieldtype(parser.get( self.__section, key))
            except:
                value = default

            self[key] = value
            if value == default:
                style = pango.STYLE_NORMAL
            else:
                style = pango.STYLE_ITALIC

            self.__model.append([key, self.type_as_string(fieldtype), str(value), fieldtype, fieldtype is not bool, style, fieldtype is bool, bool(value)])

    def model(self):
        return self.__model

    def toggle_flag(self, name):
        if name in self.Settings:
            (fieldtype, default) = self.Settings[name]
            if fieldtype == bool:
                setattr(self, name, not getattr(self, name))
            else:
                log('Cannot toggle value: %s (not boolean)', name, sender=self)
        else:
            log('Invalid setting name: %s', name, sender=self)

    def update_field(self, name, new_value):
        if name in self.Settings:
            (fieldtype, default) = self.Settings[name]
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

    def type_as_string(self, type):
        if type == int:
            return _('Integer')
        elif type == float:
            return _('Float')
        elif type == bool:
            return _('Boolean')
        else:
            return _('String')

    def __setattr__( self, name, value):
        if name in self.Settings:
            ( fieldtype, default ) = self.Settings[name]
            try:
                if self[name] != fieldtype(value):
                    log( 'Update: %s = %s', name, value, sender = self)
                    old_value = self[name]
                    self[name] = fieldtype(value)
                    for observer in self.__observers:
                        try:
                            # Notify observer about config change
                            observer(name, old_value, self[name])
                        except:
                            log('Error while calling observer: %s', repr(observer), sender=self)
                    for row in self.__model:
                        if row[0] == name:
                            value = fieldtype(value)
                            row[2] = str(value)
                            row[7] = bool(value)
                            if self[name] == default:
                                style = pango.STYLE_NORMAL
                            else:
                                style = pango.STYLE_ITALIC
                            row[5] = style
                    self.schedule_save()
            except:
                raise ValueError( '%s has to be of type %s' % ( name, fieldtype.__name__ ))
        else:
            object.__setattr__( self, name, value)

