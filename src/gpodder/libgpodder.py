

#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, 
# MA  02110-1301, USA.
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

from xml.sax.saxutils import DefaultHandler
from xml.sax import make_parser
from string import strip
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
from os import mkdir
from os import rmdir
from os import makedirs
from os import environ
from os import system
from os import unlink
from os import listdir
from os import access
from os import W_OK
from glob import glob

# for the desktop symlink stuff:
from os import symlink
from os import stat
from stat import S_ISLNK
from stat import ST_MODE

from librssreader import rssReader
from libpodcasts import podcastChannel
from libpodcasts import DownloadHistory
from libpodcasts import PlaybackHistory
from libplayers import dotdesktop_command

from gtk.gdk import PixbufLoader

from ConfigParser import ConfigParser

from xml.sax import saxutils


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
        self.createIfNecessary( self.gpodderdir)
        self.__download_dir = None
        self.cachedir = self.gpodderdir + "cache/"
        self.createIfNecessary( self.cachedir)
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
        self.show_played = False
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
        self.default_new = 1
        self.mp3_player_folder = ""
        self.only_sync_not_played = False
        self.__download_history = DownloadHistory( self.get_download_history_filename())
        self.__playback_history = PlaybackHistory( self.get_playback_history_filename())
        self.loadConfig()
    
    def createIfNecessary( self, path):
        if not exists( path):
            try:
                makedirs( path)
                return True
            except:
                log( 'Could not create %s', path)
                return False
        
        return True
    
    def getConfigFilename( self):
        return self.gpodderdir + "gpodder.conf"

    def getChannelsFilename( self):
        return self.gpodderdir + "channels.xml"

    def get_download_history_filename( self):
        return self.gpodderdir + 'download-history.txt'

    def get_playback_history_filename( self):
        return self.gpodderdir + 'playback-history.txt'

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
                self.deleteFilename( tempfile)

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
        self.write_to_parser( parser, 'show_played', self.show_played)
        self.write_to_parser( parser, 'update_tags', self.update_tags)
        self.write_to_parser( parser, 'opml_url', self.opml_url)
        self.write_to_parser( parser, 'download_dir', self.downloaddir)
        self.write_to_parser( parser, 'bittorrent_dir', self.torrentdir)
        self.write_to_parser( parser, 'use_gnome_bittorrent', self.use_gnome_bittorrent)
        self.write_to_parser( parser, 'device_type', self.device_type)
        self.write_to_parser( parser, 'main_window_width', self.main_window_width)
        self.write_to_parser( parser, 'max_downloads', self.max_downloads)
        self.write_to_parser( parser, 'max_downloads_enabled', self.max_downloads_enabled)
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

    def sanitize_feed_url( self, url):
        if not url or len(url) < 7:
            return None

        if url[:4] == 'feed':
            url = 'http' + url[4:]
        
        if url[:4] == 'http' or result[:3] == 'ftp':
            return url

        return None

    def escape_html( self, s):
        return s.replace( '&', '&amp;').replace( '<', '&lt;').replace( '>', '&gt;')

    def get_download_dir( self):
        self.createIfNecessary( self.__download_dir)
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

    def history_mark_downloaded( self, url):
        self.__download_history.add_item( url)

    def history_mark_played( self, url):
        self.__playback_history.add_item( url)

    def can_write_directory( self, directory):
        return isdir( directory) and access( directory, W_OK)

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
                    self.show_played = self.get_boolean_from_parser(parser, 'show_played', default=False)
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
                    self.default_new = self.get_int_from_parser( parser, 'default_new', 1)
                    self.mp3_player_folder = self.get_from_parser( parser, 'mp3_player_folder', '/media/usbdisk')
                    self.only_sync_not_played = self.get_boolean_from_parser(parser, 'only_sync_not_played', default=False)
                else:
                    log( 'config file %s has no section %s', fn, gpodderconf_section)
            if not self.proxy_use_environment:
                self.http_proxy = strip( http)
                self.ftp_proxy = strip( ftp)
            if strip( app) != '':
                self.open_app = strip( app)
            else:
                self.open_app = 'gnome-open'
            if strip( opml_url) != '':
                self.opml_url = strip( opml_url)
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
        filename = channel.getPodcastFilename( episode.url)

        log( 'Opening %s (with %s)', filename, self.open_app)

        # use libplayers to create a commandline out of open_app plus filename, then exec in background ('&')
        system( '%s &' % dotdesktop_command( self.open_app, filename))

    def getDesktopSymlink( self):
        symlink_path = expanduser( "~/Desktop/%s" % self.desktop_link)
        try:
            return lexists( symlink_path)
        except:
            return exists( symlink_path)

    def get_size( self, filename):
        if dirname( filename) == '/':
            return 0L
        if isfile( filename):
            return getsize( filename)
        elif isdir( filename):
            sum = getsize( filename)
            for item in listdir( filename):
                try:
                    sum = sum + self.get_size( join( filename, item))
                except:
                    return 0L
            return sum
        else:
            log( 'Cannot get size for %s' % ( filename, ))
            return 0L

    def size_to_string( self, size, method = None):
        methods = {
            'GB': 1073741824.0,
            'MB': 1048576.0,
            'KB': 1024.0,
            'B': 1.0,
        }

        size = float(size)

        if method not in methods:
            method = 'B'
            for trying in ( 'KB', 'MB', 'GB'):
                if size >= methods[trying]:
                    method = trying

        return '%.2f %s' % ( size / methods[method], method, )

    def createDesktopSymlink( self):
        if not self.getDesktopSymlink():
            downloads_path = expanduser( "~/Desktop/")
            self.createIfNecessary( downloads_path)
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
            self.deleteFilename( cover_file)
        
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
        if not url:
            return

        args = ( url, callback_pixbuf, callback_status, callback_finished, cover_file )
        thread = threading.Thread( target = self.image_download_thread, args = args)
        thread.start()

    def deleteFilename( self, filename):
        log( 'deleteFilename: %s', filename)
        try:
            unlink( filename)
            # if libipodsync extracted the cover file, remove it here
            cover_filename = filename + '.cover.jpg'
            if isfile( cover_filename):
                unlink( cover_filename)
        except:
            # silently ignore 
            pass
            
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

class gPodderChannelWriter( object):
    def write( self, channels):
        filename = gPodderLib().getChannelsFilename()
        fd = open( filename, "w")
        print >> fd, '<!-- '+_('gPodder channel list')+' -->'
        print >> fd, '<channels>'
        for chan in channels:
            try:
                print >> fd, "  <channel>\n    <url>%s</url>\n  </channel>\n" % saxutils.escape( chan.url)
            except:
                log( 'Could not write channels to file.')
        print >> fd, '</channels>'
        fd.close()

class gPodderChannelReader( DefaultHandler):
    def __init__( self):
        self.channels = []
        self.current_item = None
        self.current_element_data = ''
        self.is_cancelled = False

    def cancel( self):
        self.is_cancelled = True

    def callback_is_cancelled( self):
        return self.is_cancelled
    
    def read( self, force_update = False, callback_proc = None, callback_url = None, callback_error = None):
        """Read channels from a file into gPodder's cache

        force_update:   When true, re-download even if the cache file 
                        already exists locally

        callback_proc:  A function that takes two integer parameters, 
                        the first being the number of the currently 
                        processed item and the second being the count 
                        of the items that will be read/updated.

        callback_url:   A function that takes one string parameter
                        that contains the URL of the channel that 
                        is being updated at the moment. Will be 
                        called for every channel to be updated.

        callback_error: A function that takes one string parameter 
                        that contains a error message to be displayed.
        """

        self.channels = []

        parser = make_parser()
        parser.setContentHandler( self)

        if exists( gPodderLib().getChannelsFilename()):
            parser.parse( gPodderLib().getChannelsFilename())
        else:
            return []

        reader = rssReader()
        input_channels = []
        
        channel_count = len( self.channels)
        position = 0
        for channel in self.channels:
            if callback_proc:
                callback_proc( position, channel_count)

            if callback_url:
                callback_url( channel.url)

            cachefile = channel.downloadRss( force_update, callback_error = callback_error, callback_is_cancelled = self.callback_is_cancelled)
            # check if download was a success
            if cachefile != None:
                reader.parseXML( channel.url, cachefile)
                if reader.channel != None:
                    reader.channel.set_metadata_from_localdb()
                    input_channels.append( reader.channel)

            position = position + 1

        # the last call sets everything to 100% (hopefully ;)
        if callback_proc != None:
            callback_proc( position, channel_count)
        
        return input_channels
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        if name == 'channel':
            self.current_item = podcastChannel()
    
    def endElement( self, name):
        if self.current_item != None:
            if name == 'url':
                self.current_item.url = self.current_element_data
            if name == 'channel':
                self.channels.append( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


