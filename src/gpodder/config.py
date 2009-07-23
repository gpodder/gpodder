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

_ = gpodder.gettext

if gpodder.interface == gpodder.MAEMO:
    default_download_dir = '/media/mmc2/gpodder'
else:
    default_download_dir = os.path.join(os.path.expanduser('~'), 'gpodder-downloads')

gPodderSettings = {
    # General settings
    'player': (str, 'default', 
      _("The default player for all media, if set to 'default' this will "
        "attempt to use xdg-open on linux or the built-in media player on maemo.")),
    'videoplayer': (str, 'unspecified', 
      _("The default player for video, if set to 'unspecified' this will use "
        "whatever 'player' is set to.")),
    'opml_url': (str, 'http://gpodder.org/directory.opml',
      _("A URL pointing to an OPML file which can be used to bulk-add podcasts.")),
    'toplist_url': (str, 'http://gpodder.org/toplist.opml',
      _("A URL pointing to a gPodder web services top podcasts list")),
    'custom_sync_name': ( str, '{episode.basename}',
      _("The name used when copying a file to a FS-based device. Available "
        "options are: episode.basename, episode.title, episode.published")),
    'custom_sync_name_enabled': ( bool, True,
      _("Enables renaming files when transfered to an FS-based device with "
        "respect to the 'custom_sync_name'.")),
    'max_downloads': ( int, 1,
      _("The maximum number of simultaneous downloads allowed at a single "
        "time. Requires 'max_downloads_enabled'.")),
    'max_downloads_enabled': ( bool, True,
      _("The 'max_downloads' setting will only work if this is set to 'True'.")), 
    'limit_rate': ( bool, False,
      _("The 'limit_rate_value' setting will only work if this is set to 'True'.")),
    'limit_rate_value': ( float, 500.0,
      _("Set a global speed limit (in KB/s) when downloading files. "
        "Requires 'limit_rate'.")),
    'episode_old_age': ( int, 7,
      _("The number of days before an episode is considered old. "
        "Must be used in conjunction with 'auto_remove_old_episodes'.")),

    # Boolean config flags
    'update_on_startup': ( bool, False,
      _("Update the feed cache on startup.")),
    'only_sync_not_played': ( bool, False,
      _("Only sync episodes to a device that have not been marked played in gPodder.")),
    'fssync_channel_subfolders': ( bool, True,
      _("Create a directory for every feed when syncing to an FS-based device "
        "instead of putting all the episodes in a single directory.")),
    'on_sync_mark_played': ( bool, False,
      _("After syncing an episode, mark it as played in gPodder.")),
    'on_sync_delete': ( bool, False,
      _("After syncing an episode, delete it from gPodder.")),
    'auto_remove_old_episodes': ( bool, False,
      _("Remove episodes older than 'episode_old_age' days on startup.")),
    'auto_update_feeds': (bool, False,
      _("Automatically update feeds when gPodder is minimized. "
        "See 'auto_update_frequency' and 'auto_download'.")),
    'auto_update_frequency': (int, 20,
      _("The frequency (in minutes) at which gPodder will update all feeds "
        "if 'auto_update_feeds' is enabled.")),
    'episode_list_descriptions': (bool, True,
      _("Display the episode's description under the episode title in the GUI.")),
    'show_toolbar': (bool, True,
      _("Show the toolbar in the GUI's main window.")),
    'ipod_purge_old_episodes': (bool, False,
      _("Remove episodes from an iPod device if they've been marked as played "
        "on the device and they have no rating set (the rating can be set on "
        "the device by the user to prevent deletion).")),
    'ipod_delete_played_from_db': (bool, False,
      _("Remove episodes from gPodder if they've been marked as played "
        "on the device and they have no rating set (the rating can be set on "
        "the device by the user to prevent deletion).")),
    'mp3_player_delete_played': (bool, False,
      _("Removes episodes from an FS-based device that have been marked as "
        "played in gPodder. Note: only works if 'only_sync_not_played' is "
        "also enabled.")),
    'disable_pre_sync_conversion': (bool, False,
      _("Disable pre-synchronization conversion of OGG files. This should be "
        "enabled for deviced that natively support OGG. Eg. Rockbox, iAudio")),
    
    # Tray icon and notification settings
    'display_tray_icon': (bool, False,
      _("Whether or not gPodder should display an icon in the system tray.")),
    'minimize_to_tray': (bool, False,
      _("If 'display_tray_icon' is enabled, when gPodder is minimized it will "
        "not be visible in the window list.")),  
    'start_iconified': (bool, False,
      _("When gPodder starts, send it to the tray immediately.")),
    'enable_notifications': (bool, True,
      _("Let gPodder use notification bubbles when it can completed certain "
        "tasks like downloading an episode or finishing syncing to a device.")),
    'on_quit_ask': (bool, True,
      _("Ask the user to confirm quitting the application.")),
    'auto_download': (str, 'never',
      _("Auto download episodes (never, minimized, always)")),
    'do_not_show_new_episodes_dialog': (bool, False,
      _("Do not show the new episodes dialog after updating feed cache when "
        "gPodder is not minimized")),


    # Settings that are updated directly in code
    'ipod_mount': ( str, '/media/ipod',
      _("The moint point for an iPod Device.")),
    'mp3_player_folder': ( str, '/media/usbdisk',
      _("The moint point for an FS-based device.")),
    'device_type': ( str, 'none',
      _("The device type: 'mtp', 'filesystem' or 'ipod'")),
    'download_dir': (str, default_download_dir,
      _("The default directory that podcast episodes are downloaded to.")),

    # Playlist Management settings
    'mp3_player_playlist_file': (str, 'PLAYLISTS/gpodder.m3u',
      _("The relative path to where the playlist is stored on an FS-based device.")),
    'mp3_player_playlist_absolute_path': (bool, True,
      _("Whether or not the the playlist should contain relative or absolute "
        "paths; this is dependent on the player.")),
    'mp3_player_playlist_win_path': (bool, True,
      _("Whether or not the player requires Windows-style paths in the playlist.")),

    # Special settings (not in preferences)
    'on_quit_systray': (bool, False,
      _("When the 'X' button is clicked do not quit, send gPodder to the tray.")),
    'max_episodes_per_feed': (int, 200,
      _("The maximum number of episodes that gPodder will display in the episode "
        "list. Note: Set this to a lower value on slower hardware to speed up "
        "rendering of the episode list.")),
    'mp3_player_use_scrobbler_log': (bool, False,
      _("Attempt to use a Device's scrobbler.log to mark episodes as played in "
        "gPodder. Useful for Rockbox players.")),
    'mp3_player_max_filename_length': (int, 100,
      _("The maximum filename length for FS-based devices.")),
    'show_url_entry_in_podcast_list': (bool, False,
      _("Whether or not to show the URL entry (add podcast) box in the main window.")),
    'rockbox_copy_coverart' : (bool, False,
      _("Create rockbox-compatible coverart and copy it to the device when "
        "syncing. See: 'rockbox_coverart_size'.")),
    'rockbox_coverart_size' : (int, 100,
      _("The width of the coverart for the user's Rockbox player/skin.")),
    'custom_player_copy_coverart' : (bool, False,
      _("Create custom coverart for FS-based players.")),
    'custom_player_coverart_size' : (int, 176,
      _("The width of the coverart for the user's FS-based player.")),
    'custom_player_coverart_name' : (str, 'folder.jpg',
      _("The name of the coverart file accepted by the user's FS-based player.")),
    'custom_player_coverart_format' : (str, 'JPEG',
      _("The image format accepted by the user's FS-based player.")),
    'podcast_list_icon_size': (int, 32,
      _("The width of the icon used in the podcast channel list.")),
    'cmd_all_downloads_complete': (str, '',
      _("The path to a command that gets run after all downloads are completed.")),
    'cmd_download_complete': (str, '',
      _("The path to a command that gets run after a single download completes. "
        "See http://wiki.gpodder.org/wiki/Time_stretching for more info.")),
    'log_sqlite': (bool, False,
      _("Enable _very_ verbose logging from the dbsqlite module.")),
    'enable_html_shownotes': (bool, True,
      _("Allow HTML to be rendered in the episode information dialog.")),
    'maemo_enable_gestures': (bool, False,
      _("Enable fancy gestures on Maemo.")),
    'sync_disks_after_transfer': (bool, True,
      _("Call 'sync' after tranfering episodes to a device.")),
    'resume_ask_every_episode': (bool, False,
      _("If there are episode downloads that can be resumed, ask whether or "
        "not to resume every single one.")),
    'disable_fingerscroll': (bool, False,
      _("Disable the use of finger-scrollable widgets on Maemo.")),
    'double_click_episode_action': (str, 'shownotes',
      _("Episode double-click/enter action handler (shownotes, download, stream)")),

    # Settings for my.gpodder.org
    'my_gpodder_username': (str, '',
      _("The user's gPodder web services username.")),
    'my_gpodder_password': (str, '',
      _("The user's gPodder web services password.")),
    'my_gpodder_autoupload': (bool, False,
      _("Upload the user's podcast list to the gPodder web services when "
        "gPodder is closed.")),

    # Paned position
    'paned_position': ( int, 200,
      _("The width of the channel list.")),
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
            ( fieldtype, default ) = self.Settings[name][:2]
            return self[name]
        else:
            raise AttributeError('%s is not a setting' % name)

    def get_description( self, option_name ):
        description = _("No description available.")
        
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

        for ( key, value ) in self.Settings.items():
            ( fieldtype, default ) = value[:2]
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
            (fieldtype, default) = self.Settings[key][:2]
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
            ( fieldtype, default ) = self.Settings[name][:2]
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

