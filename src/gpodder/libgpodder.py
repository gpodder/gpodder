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
#  libgpodder.py -- gpodder configuration
#  thomas perl <thp@perli.net>   20051030
#
#

import gtk
import gobject
import thread
import threading
import urllib
import shutil

from gpodder import util
from gpodder import opml

from os.path import expanduser
from os.path import exists
from os.path import splitext
from liblogger import log
try:
    from os.path import lexists
except:
    log( 'lexists() not found in module os.path - (using Python < 2.4?) - will fallback to exists()')
from os.path import dirname
from os.path import basename
from os.path import isfile
from os.path import isdir
from os.path import islink
from os.path import getsize
from os.path import join
import os.path
from os import mkdir
from os import rmdir
from os import makedirs
from os import environ
from os import system
from os import unlink
from os import listdir
from glob import glob

# for the desktop symlink stuff:
from os import symlink
from os import stat
from stat import S_ISLNK
from stat import ST_MODE

from libplayers import dotdesktop_command

from types import ListType

from gtk.gdk import PixbufLoader

from ConfigParser import ConfigParser

from xml.sax import saxutils

from urlparse import urlparse

from subprocess import Popen
import shlex

# global recursive lock for thread exclusion
globalLock = threading.RLock()

# my gpodderlib variable
g_podder_lib = None

# default url to use for opml directory on the web
default_opml_directory = 'http://gpodder.berlios.de/directory.opml'

def getLock():
    globalLock.acquire()

def releaseLock():
    globalLock.release()

# some awkward kind of "singleton" ;)
def gPodderLib():
    global g_podder_lib
    if g_podder_lib == None:
        g_podder_lib = gPodderLibClass()
    return g_podder_lib

class gPodderLibClass( object):
    gpodderconf_section = 'gpodder-conf-1'
    
    def __init__( self):
        self.gpodderdir = expanduser( "~/.config/gpodder/")
        util.make_directory( self.gpodderdir)
        self.feed_cache_file = os.path.join( self.gpodderdir, 'feedcache.db')
        self.channel_settings_file = os.path.join( self.gpodderdir, 'channelsettings.db')
        self.channel_opml_file = os.path.join( self.gpodderdir, 'channels.opml')
        self.__download_dir = None
        try:
            self.http_proxy = environ['http_proxy']
        except:
            self.http_proxy = ''
        try:
            self.ftp_proxy = environ['ftp_proxy']
        except:
            self.ftp_proxy = ''
        self.proxy_use_environment = True 
        self.open_app = ""
        self.ipod_mount = ""
        self.opml_url = ""
        self.update_on_startup = False
        self.download_after_update = True
        self.torrentdir = expanduser('~/gpodder-downloads/torrents')
        self.use_gnome_bittorrent = True
        self.limit_rate = False
        self.limit_rate_value = 4.0
        self.update_tags = False
        self.desktop_link = _("gPodder downloads")
        self.device_type = None
        self.main_window_width = 600
        self.main_window_height = 450
        self.main_window_x = 0
        self.main_window_y = 0
        self.paned_position = 150
        self.max_downloads = 3
        self.max_downloads_enabled = False
        self.custom_sync_name_enabled = False
        self.custom_sync_name = '{episode.title}'
        self.default_new = 1
        self.mp3_player_folder = ""
        self.only_sync_not_played = False
        self.__download_history = DownloadHistory( self.get_download_history_filename())
        self.__playback_history = PlaybackHistory( self.get_playback_history_filename())
        self.loadConfig()
    
    def getConfigFilename( self):
        return self.gpodderdir + "gpodder.conf"

    def getChannelsFilename( self):
        return self.gpodderdir + "channels.xml"

    def get_download_history_filename( self):
        return self.gpodderdir + 'download-history.txt'

    def get_playback_history_filename( self):
        return self.gpodderdir + 'playback-history.txt'

    def get_device_name( self):
        if self.device_type == 'ipod':
            return _('iPod')
        elif self.device_type == 'filesystem':
            return _('MP3 player')
        else:
            log( 'Warning: Called get_device_name() when no device was selected.', sender = self)
            return '(unknown device)'

    def propertiesChanged( self):
        # set new environment variables for subprocesses to use,
        # but only if we are not told to passthru the env vars
        if not self.proxy_use_environment:
            environ['http_proxy'] = self.http_proxy
            environ['ftp_proxy'] = self.ftp_proxy
        # save settings for next startup
        self.saveConfig()

    def clean_up_downloads( self, delete_partial = False):
        # Clean up temporary files left behind by old gPodder versions
        if delete_partial:
            temporary_files = glob( '%s/*/.tmp-*' % ( self.downloaddir, ))
            for tempfile in temporary_files:
                util.delete_file( tempfile)

        # Clean up empty download folders
        download_dirs = glob( '%s/*' % ( self.downloaddir, ))
        for ddir in download_dirs:
            if isdir( ddir):
                globr = glob( '%s/*' % ( ddir, ))
                if not globr and ddir != self.torrentdir:
                    log( 'Stale download directory found: %s', basename( ddir))
                    try:
                        rmdir( ddir)
                        log( 'Successfully removed %s.', ddir)
                    except:
                        log( 'Could not remove %s.', ddir)

    def saveConfig( self):
        parser = ConfigParser()
        self.write_to_parser( parser, 'http_proxy', self.http_proxy)
        self.write_to_parser( parser, 'ftp_proxy', self.ftp_proxy)
        self.write_to_parser( parser, 'player', self.open_app)
        self.write_to_parser( parser, 'proxy_use_env', self.proxy_use_environment)
        self.write_to_parser( parser, 'ipod_mount', self.ipod_mount)
        self.write_to_parser( parser, 'update_on_startup', self.update_on_startup)
        self.write_to_parser( parser, 'download_after_update', self.download_after_update)
        self.write_to_parser( parser, 'limit_rate', self.limit_rate)
        self.write_to_parser( parser, 'limit_rate_value', self.limit_rate_value)
        self.write_to_parser( parser, 'update_tags', self.update_tags)
        self.write_to_parser( parser, 'opml_url', self.opml_url)
        self.write_to_parser( parser, 'download_dir', self.downloaddir)
        self.write_to_parser( parser, 'bittorrent_dir', self.torrentdir)
        self.write_to_parser( parser, 'use_gnome_bittorrent', self.use_gnome_bittorrent)
        self.write_to_parser( parser, 'device_type', self.device_type)
        self.write_to_parser( parser, 'main_window_width', self.main_window_width)
        self.write_to_parser( parser, 'max_downloads', self.max_downloads)
        self.write_to_parser( parser, 'max_downloads_enabled', self.max_downloads_enabled)
        self.write_to_parser( parser, 'custom_sync_name', self.custom_sync_name)
        self.write_to_parser( parser, 'custom_sync_name_enabled', self.custom_sync_name_enabled)
        self.write_to_parser( parser, 'default_new', self.default_new)
        self.write_to_parser( parser, 'main_window_height', self.main_window_height)
        self.write_to_parser( parser, 'main_window_x', self.main_window_x)
        self.write_to_parser( parser, 'main_window_y', self.main_window_y)
        self.write_to_parser( parser, 'paned_position', self.paned_position)
        self.write_to_parser( parser, 'mp3_player_folder', self.mp3_player_folder)
        self.write_to_parser( parser, 'only_sync_not_played', self.only_sync_not_played)
        fn = self.getConfigFilename()
        fp = open( fn, "w")
        parser.write( fp)
        fp.close()

    def get_download_dir( self):
        util.make_directory( self.__download_dir)
        return self.__download_dir

    def set_download_dir( self, new_downloaddir):
        if self.__download_dir and self.__download_dir != new_downloaddir:
            log( 'Moving downloads from %s to %s', self.__download_dir, new_downloaddir)
            try:
                # Save state of Symlink on Desktop
                generate_symlink = False
                if self.getDesktopSymlink():
                    log( 'Desktop symlink exists before move.')
                    generate_symlink = True

                # Fix error when moving over disk boundaries
                if isdir( new_downloaddir) and not listdir( new_downloaddir):
                    rmdir( new_downloaddir)

                shutil.move( self.__download_dir, new_downloaddir)

                if generate_symlink:
                    # Re-generate Symlink on Desktop
                    log( 'Will re-generate desktop symlink to %s.', new_downloaddir)
                    self.removeDesktopSymlink()
                    self.__download_dir = new_downloaddir
                    self.createDesktopSymlink()
            except:
                log( 'Error while moving %s to %s.', self.__download_dir, new_downloaddir)
                return

        self.__download_dir = new_downloaddir

    downloaddir = property(fget=get_download_dir,fset=set_download_dir)

    def history_mark_downloaded( self, url, add_item = True):
        if add_item:
            self.__download_history.add_item( url)
        else:
            self.__download_history.del_item( url)

    def history_mark_played( self, url, add_item = True):
        if add_item:
            self.__playback_history.add_item( url)
        else:
            self.__playback_history.del_item( url)

    def history_is_downloaded( self, url):
        return (url in self.__download_history)

    def history_is_played( self, url):
        return (url in self.__playback_history)

    def get_from_parser( self, parser, option, default = ''):
        try:
            result = parser.get( self.gpodderconf_section, option)
            return result
        except:
            return default

    def get_int_from_parser( self, parser, option, default = 0):
        try:
            result = int(parser.get( self.gpodderconf_section, option))
            return result
        except:
            return default

    def get_float_from_parser( self, parser, option, default = 1.0):
        try:
            result = float(parser.get( self.gpodderconf_section, option))
            return result
        except:
            return default

    def get_boolean_from_parser( self, parser, option, default = False):
        try:
            result = parser.getboolean( self.gpodderconf_section, option)
            return result
        except:
            return default

    def write_to_parser( self, parser, option, value = ''):
        if not parser.has_section( self.gpodderconf_section):
            parser.add_section( self.gpodderconf_section)
        try:
            parser.set( self.gpodderconf_section, option, str(value))
        except:
            log( 'write_to_parser: could not write config (option=%s, value=%s)', option, value)
    
    def loadConfig( self):
        was_oldstyle = False
        try:
            fn = self.getConfigFilename()
            if open(fn,'r').read(1) != '[':
                log( 'seems like old-style config. trying to read it anyways..')
                fp = open( fn, 'r')
                http = fp.readline()
                ftp = fp.readline()
                app = fp.readline()
                fp.close()
                was_oldstyle = True
            else:
                parser = ConfigParser()
                parser.read( fn)
                if parser.has_section( self.gpodderconf_section):
                    http = self.get_from_parser( parser, 'http_proxy')
                    ftp = self.get_from_parser( parser, 'ftp_proxy')
                    app = self.get_from_parser( parser, 'player', 'gnome-open')
                    opml_url = self.get_from_parser( parser, 'opml_url', default_opml_directory)
                    if opml_url == 'http://share.opml.org/opml/topPodcasts.opml':
                        opml_url = 'http://gpodder.berlios.de/directory.opml'
                    self.proxy_use_environment = self.get_boolean_from_parser( parser, 'proxy_use_env', True)
                    self.ipod_mount = self.get_from_parser( parser, 'ipod_mount', '/media/ipod')
                    self.update_on_startup = self.get_boolean_from_parser(parser, 'update_on_startup', default=False)
                    self.download_after_update = self.get_boolean_from_parser(parser, 'download_after_update', default=False)
                    self.limit_rate = self.get_boolean_from_parser(parser, 'limit_rate', default=False)
                    self.limit_rate_value = self.get_float_from_parser(parser, 'limit_rate_value', default=4.0)
                    self.update_tags = self.get_boolean_from_parser(parser, 'update_tags', default=False)
                    self.downloaddir = self.get_from_parser( parser, 'download_dir', expanduser('~/gpodder-downloads'))
                    self.torrentdir = self.get_from_parser( parser, 'bittorrent_dir', expanduser('~/gpodder-downloads/torrents'))
                    self.use_gnome_bittorrent = self.get_boolean_from_parser( parser, 'use_gnome_bittorrent', default=True)
                    self.device_type = self.get_from_parser( parser, 'device_type', 'none')
                    self.main_window_width = self.get_int_from_parser( parser, 'main_window_width', 600)
                    self.main_window_height = self.get_int_from_parser( parser, 'main_window_height', 450)
                    self.main_window_x = self.get_int_from_parser( parser, 'main_window_x', 0)
                    self.main_window_y = self.get_int_from_parser( parser, 'main_window_y', 0)
                    self.paned_position = self.get_int_from_parser( parser, 'paned_position', 0)
                    self.max_downloads = self.get_int_from_parser( parser, 'max_downloads', 3)
                    self.max_downloads_enabled = self.get_boolean_from_parser(parser, 'max_downloads_enabled', default=False)
                    self.custom_sync_name = self.get_from_parser( parser, 'custom_sync_name', '')
                    self.custom_sync_name_enabled = self.get_boolean_from_parser(parser, 'custom_sync_name_enabled', default=False)
                    self.default_new = self.get_int_from_parser( parser, 'default_new', 1)
                    self.mp3_player_folder = self.get_from_parser( parser, 'mp3_player_folder', '/media/usbdisk')
                    self.only_sync_not_played = self.get_boolean_from_parser(parser, 'only_sync_not_played', default=False)
                else:
                    log( 'config file %s has no section %s', fn, gpodderconf_section)
            if not self.proxy_use_environment:
                self.http_proxy = http.strip()
                self.ftp_proxy = ftp.strip()
            if app.strip():
                self.open_app = app.strip()
            else:
                self.open_app = 'gnome-open'
            if opml_url.strip():
                self.opml_url = opml_url.strip()
            else:
                self.opml_url = default_opml_directory
        except:
            # TODO: well, well.. (http + ftp?)
            self.open_app = 'gnome-open'
            self.ipod_mount = '/media/ipod'
            self.device_type = 'none'
            self.main_window_width = 600
            self.main_window_height = 450
            self.main_window_x = 0
            self.main_window_y = 0
            self.paned_position = 150
            self.mp3_player_folder = '/media/usbdisk'
            self.opml_url = default_opml_directory
            self.downloaddir = expanduser('~/gpodder-downloads')
            self.torrentdir = expanduser('~/gpodder-downloads/torrents')
            self.use_gnome_bittorrent = True
        if was_oldstyle:
            self.saveConfig()

    def playback_episode( self, channel, episode):
        self.history_mark_played( episode.url)
        filename = episode.local_filename()

        command_line = shlex.split( dotdesktop_command( self.open_app, filename).encode('utf-8'))
        log( 'Command line: [ %s ]', ', '.join( [ '"%s"' % p for p in command_line ]), sender = self)
        try:
            Popen( command_line)
        except:
            return ( False, command_line[0] )
        return ( True, command_line[0] )

    def getDesktopSymlink( self):
        symlink_path = expanduser( "~/Desktop/%s" % self.desktop_link)
        try:
            return lexists( symlink_path)
        except:
            return exists( symlink_path)

    def createDesktopSymlink( self):
        if not self.getDesktopSymlink():
            downloads_path = expanduser( "~/Desktop/")
            util.make_directory( downloads_path)
            symlink( self.downloaddir, "%s%s" % (downloads_path, self.desktop_link))
    
    def removeDesktopSymlink( self):
        if self.getDesktopSymlink():
            unlink( expanduser( "~/Desktop/%s" % self.desktop_link))

    def image_download_thread( self, url, callback_pixbuf = None, callback_status = None, callback_finished = None, cover_file = None):
        if callback_status != None:
            gobject.idle_add( callback_status, _('Downloading channel cover...'))
        pixbuf = PixbufLoader()
        
        if cover_file == None:
            log( 'Downloading %s', url)
            pixbuf.write( urllib.urlopen(url).read())
        
        if cover_file != None and not exists( cover_file):
            log( 'Downloading cover to %s', cover_file)
            cachefile = open( cover_file, "w")
            cachefile.write( urllib.urlopen(url).read())
            cachefile.close()
        
        if cover_file != None:
            log( 'Reading cover from %s', cover_file)
            pixbuf.write( open( cover_file, "r").read())
        
        try:
            pixbuf.close()
        except:
            # data error, delete temp file
            util.delete_file( cover_file)
        
        MAX_SIZE = 400
        if callback_pixbuf != None:
            pb = pixbuf.get_pixbuf()
            if pb:
                if pb.get_width() > MAX_SIZE:
                    factor = MAX_SIZE*1.0/pb.get_width()
                    pb = pb.scale_simple( int(pb.get_width()*factor), int(pb.get_height()*factor), gtk.gdk.INTERP_BILINEAR)
                if pb.get_height() > MAX_SIZE:
                    factor = MAX_SIZE*1.0/pb.get_height()
                    pb = pb.scale_simple( int(pb.get_width()*factor), int(pb.get_height()*factor), gtk.gdk.INTERP_BILINEAR)
                gobject.idle_add( callback_pixbuf, pb)
        if callback_status != None:
            gobject.idle_add( callback_status, '')
        if callback_finished != None:
            gobject.idle_add( callback_finished)

    def get_image_from_url( self, url, callback_pixbuf = None, callback_status = None, callback_finished = None, cover_file = None):
        if not url and not os.path.exists( cover_file):
            return

        args = ( url, callback_pixbuf, callback_status, callback_finished, cover_file )
        thread = threading.Thread( target = self.image_download_thread, args = args)
        thread.start()

    def invoke_torrent( self, url, torrent_filename, target_filename):
        self.history_mark_played( url)

        if self.use_gnome_bittorrent:
            command = 'gnome-btdownload "%s" --saveas "%s"' % ( torrent_filename, join( self.torrentdir, target_filename))
            log( command, sender = self)
            system( '%s &' % command)
        else:
            # Simply copy the .torrent with a suitable name
            try:
                target_filename = join( self.torrentdir, splitext( target_filename)[0] + '.torrent')
                shutil.copyfile( torrent_filename, target_filename)
            except:
                log( 'Torrent copy failed: %s => %s.', torrent_filename, target_filename)


class DownloadHistory( ListType):
    def __init__( self, filename):
        self.filename = filename
        try:
            self.read_from_file()
        except:
            log( 'Creating new history list.', sender = self)

    def read_from_file( self):
        for line in open( self.filename, 'r'):
            self.append( line.strip())

    def save_to_file( self):
        if len( self):
            fp = open( self.filename, 'w')
            for url in self:
                fp.write( url + "\n")
            fp.close()
            log( 'Wrote %d history entries.', len( self), sender = self)

    def add_item( self, data, autosave = True):
        affected = 0
        if data and type( data) is ListType:
            # Support passing a list of urls to this function
            for url in data:
                affected = affected + self.add_item( url, autosave = False)
        else:
            if data not in self:
                log( 'Adding: %s', data, sender = self)
                self.append( data)
                affected = affected + 1

        if affected and autosave:
            self.save_to_file()

        return affected

    def del_item( self, data, autosave = True):
        affected = 0
        if data and type( data) is ListType:
            # Support passing a list of urls to this function
            for url in data:
                affected = affected + self.del_item( url, autosave = False)
        else:
            if data in self:
                log( 'Removing: %s', data, sender = self)
                self.remove( data)
                affected = affected + 1

        if affected and autosave:
            self.save_to_file()

        return affected


class PlaybackHistory( DownloadHistory):
    pass

