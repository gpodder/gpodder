# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

from gpodder import util
from gpodder.liblogger import log

import atexit
import os.path
import time
import threading
import ConfigParser

gPodderSettings = {
    # General settings
    'player': ( str, 'xdg-open' ),
    'videoplayer': (str, 'unspecified'),
    'opml_url': ( str, 'http://gpodder.berlios.de/directory.opml' ),
    'http_proxy': ( str, '' ),
    'ftp_proxy': ( str, '' ),
    'custom_sync_name': ( str, '{episode.basename}' ),
    'custom_sync_name_enabled': ( bool, True ),
    'max_downloads': ( int, 3 ),
    'max_downloads_enabled': ( bool, False ), 
    'limit_rate': ( bool, False ),
    'limit_rate_value': ( float, 500.0 ),
    'bittorrent_dir': ( str, os.path.expanduser( '~/gpodder-downloads/torrents') ),
    'episode_old_age': ( int, 7 ),

    # Boolean config flags
    'update_on_startup': ( bool, False ),
    'auto_download_when_minimized': (bool, False),
    'use_gnome_bittorrent': ( bool, True ),
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
    
    # Tray icon and notification settings
    'display_tray_icon': (bool, False),
    'minimize_to_tray': (bool, False),  
    'start_iconified': (bool, False),
    'enable_notifications': (bool, True),
    'on_quit_ask': (bool, True),

    # Bluetooth-related settings
    'bluetooth_enabled': (bool, False),
    'bluetooth_ask_always': (bool, True),
    'bluetooth_ask_never': (bool, False),
    'bluetooth_device_name': (str, 'No device'),
    'bluetooth_device_address': (str, '00:00:00:00:00:00'),
    'bluetooth_use_converter': (bool, False),
    'bluetooth_converter': (str, ''),

    # Settings that are updated directly in code
    'ipod_mount': ( str, '/media/ipod' ),
    'mp3_player_folder': ( str, '/media/usbdisk' ),
    'device_type': ( str, 'none' ),
    'download_dir': ( str, os.path.expanduser( '~/gpodder-downloads') ),

    # Special settings (not in preferences)
    'default_new': ( int, 1 ),
    'use_si_units': ( bool, False ),
    'on_quit_systray': (bool, False),

    # Window and paned positions
    'main_window_x': ( int, 100 ),
    'main_window_y': ( int, 100 ),
    'main_window_width': ( int, 700 ),
    'main_window_height': ( int, 500 ),
    'paned_position': ( int, 200 ),
}

class Config(dict):
    Settings = gPodderSettings

    def __init__( self, filename = 'gpodder.conf'):
        dict.__init__( self)
        self.__save_thread = None
        self.__filename = filename
        self.__section = 'gpodder-conf-1'
        self.__ignore_window_events = False
        # Name, Type, Value, Type(python type), Editable?, Font weight
        self.__model = gtk.ListStore(str, str, str, object, bool, int)

        atexit.register( self.__atexit)

        self.load()
    
    def __getattr__( self, name):
        if name in self.Settings:
            ( fieldtype, default ) = self.Settings[name]
            return self[name]
        else:
            raise AttributeError

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

    def connect_gtk_filechooser(self, name, filechooser, is_for_files=False):
        if name in self.Settings:
            if is_for_files:
                # A FileChooser for a single file
                filechooser.set_filename(getattr(self, name))
            else:
                # A FileChooser for a folder
                filechooser.set_current_folder(getattr(self, name))
            filechooser.connect('selection-changed', lambda filechooser: setattr(self, name, filechooser.get_filename()))
        else:
            raise ValueError('%s is not a setting'%name)

    def receive_configure_event( self, widget, event, config_prefix):
        ( x, y, width, height ) = map( lambda x: config_prefix + '_' + x, [ 'x', 'y', 'width', 'height' ])
        ( x_pos, y_pos ) = widget.get_position()
        ( width_size, height_size ) = widget.get_size()
        if not self.__ignore_window_events:
            setattr( self, x, x_pos)
            setattr( self, y, y_pos)
            setattr( self, width, width_size)
            setattr( self, height, height_size)

    def enable_window_events(self):
        self.__ignore_window_events = False

    def disable_window_events(self):
        self.__ignore_window_events = True

    def connect_gtk_window( self, window, config_prefix = 'main_window'):
        ( x, y, width, height ) = map( lambda x: config_prefix + '_' + x, [ 'x', 'y', 'width', 'height' ])
        if set( ( x, y, width, height )).issubset( set( self.Settings)):
            window.resize( getattr( self, width), getattr( self, height))
            window.move( getattr( self, x), getattr( self, y))
            self.disable_window_events()
            util.idle_add(self.enable_window_events)
            window.connect( 'configure-event', self.receive_configure_event, config_prefix)
        else:
            raise ValueError( 'Missing settings in set: %s' % ', '.join( ( x, y, width, height )))

    def schedule_save( self):
        if self.__save_thread == None:
            self.__save_thread = threading.Thread( target = self.save_thread_proc)
            self.__save_thread.start()

    def save_thread_proc( self):
        for i in range( 100):
            if self.__save_thread != None:
                time.sleep( .1)
        if self.__save_thread != None:
            self.save()

    def __atexit( self):
        if self.__save_thread != None:
            self.save()

    def save( self, filename = None):
        if filename != None:
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
        if filename != None:
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
                weight = pango.WEIGHT_NORMAL
            else:
                weight = pango.WEIGHT_BOLD
            self.__model.append([key, self.type_as_string(fieldtype), str(value), fieldtype, fieldtype is not bool, weight])

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
                    self[name] = fieldtype(value)
                    for row in self.__model:
                        if row[0] == name:
                            row[2] = str(fieldtype(value))
                            if self[name] == default:
                                weight = pango.WEIGHT_NORMAL
                            else:
                                weight = pango.WEIGHT_BOLD
                            row[5] = weight
                    self.schedule_save()
            except:
                raise ValueError( '%s has to be of type %s' % ( name, fieldtype.__name__ ))
        else:
            object.__setattr__( self, name, value)

