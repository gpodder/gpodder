

#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2006 Thomas Perl <thp at perli.net>
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
import thread
import threading
import urllib

from xml.sax.saxutils import DefaultHandler
from xml.sax import make_parser
from string import strip
from os.path import expanduser
from os.path import exists
from os.path import dirname
from os import mkdir
from os import makedirs
from os import environ
from os import system
from os import unlink

# for the desktop symlink stuff:
from os import symlink
from os import stat
from stat import S_ISLNK
from stat import ST_MODE

from librssreader import rssReader
from libpodcasts import podcastChannel

from gtk.gdk import PixbufLoader

from ConfigParser import ConfigParser

from xml.sax import saxutils

# global debugging variable, set to False on release
# TODO: while developing a new version, set this to "True"
debugging = True

# global recursive lock for thread exclusion
globalLock = threading.RLock()

# my gpodderlib variable
g_podder_lib = None

def isDebugging():
    return debugging

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
    gpodderdir = ""
    downloaddir = ""
    cachedir = ""
    http_proxy = ""
    ftp_proxy = ""
    proxy_use_environment = False
    open_app = ""
    ipod_mount = ""
    desktop_link = _("gPodder downloads")
    gpodderconf_section = 'gpodder-conf-1'
    
    def __init__( self):
        self.gpodderdir = expanduser( "~/.config/gpodder/")
        self.createIfNecessary( self.gpodderdir)
        self.downloaddir = self.gpodderdir + "downloads/"
        self.createIfNecessary( self.downloaddir)
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
        self.loadConfig()
    
    def createIfNecessary( self, path):
        if not exists( path):
            try:
                makedirs( path)
                return True
            except:
                if isDebugging():
                    print 'createIfNecessary: could not create: %s' % ( path )
                return False
        
        return True
    
    def getConfigFilename( self):
        return self.gpodderdir + "gpodder.conf"

    def getChannelsFilename( self):
        return self.gpodderdir + "channels.xml"

    def propertiesChanged( self):
        # set new environment variables for subprocesses to use,
        # but only if we are not told to passthru the env vars
        if not self.proxy_use_environment:
            environ['http_proxy'] = self.http_proxy
            environ['ftp_proxy'] = self.ftp_proxy
        # save settings for next startup
        self.saveConfig()

    def saveConfig( self):
        parser = ConfigParser()
        self.write_to_parser( parser, 'http_proxy', self.http_proxy)
        self.write_to_parser( parser, 'ftp_proxy', self.ftp_proxy)
        self.write_to_parser( parser, 'player', self.open_app)
        self.write_to_parser( parser, 'proxy_use_env', self.proxy_use_environment)
        self.write_to_parser( parser, 'ipod_mount', self.ipod_mount)
        self.write_to_parser( parser, 'update_on_startup', self.update_on_startup)
        fn = self.getConfigFilename()
        fp = open( fn, "w")
        parser.write( fp)
        fp.close()

    def get_from_parser( self, parser, option, default = ''):
        try:
            result = parser.get( self.gpodderconf_section, option)
            if isDebugging():
                print "get_from_parser( %s) = %s" % ( option, result )
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
            if isDebugging():
                print 'write_to_parser: could not write config (option=%s, value=%s' % (option, value)
    
    def loadConfig( self):
        was_oldstyle = False
        try:
            fn = self.getConfigFilename()
            if open(fn,'r').read(1) != '[':
                if isDebugging():
                    print 'seems like old-style config. trying to read it anyways..'
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
                    self.proxy_use_environment = self.get_boolean_from_parser( parser, 'proxy_use_env', True)
                    self.ipod_mount = self.get_from_parser( parser, 'ipod_mount', '/media/ipod/')
                    self.update_on_startup = self.get_boolean_from_parser(parser, 'update_on_startup', default=False)
                else:
                    if isDebugging():
                        print "config file %s has no section %s" % (fn, gpodderconf_section)
            if not self.proxy_use_environment:
                self.http_proxy = strip( http)
                self.ftp_proxy = strip( ftp)
            if strip( app) != '':
                self.open_app = strip( app)
            else:
                self.open_app = 'gnome-open'
        except:
            # TODO: well, well.. (http + ftp?)
            self.open_app = 'gnome-open'
            self.ipod_mount = '/media/ipod/'
        if was_oldstyle:
            self.saveConfig()

    def openFilename( self, filename):
        if isDebugging():
            print "open " + filename + " with " + self.open_app
        system( self.open_app + " " + filename + " &")

    def getDesktopSymlink( self):
        symlink_path = expanduser( "~/Desktop/%s" % self.desktop_link)
        return exists( symlink_path)

    def createDesktopSymlink( self):
        if isDebugging():
            print "createDesktopSymlink requested"
        if not self.getDesktopSymlink():
            downloads_path = expanduser( "~/Desktop/")
            self.createIfNecessary( downloads_path)
            symlink( self.downloaddir, "%s%s" % (downloads_path, self.desktop_link))
    
    def removeDesktopSymlink( self):
        if isDebugging():
            print "removeDesktopSymlink requested"
        if self.getDesktopSymlink():
            unlink( expanduser( "~/Desktop/%s" % self.desktop_link))

    def image_download_thread( self, url, callback_pixbuf = None, callback_status = None, callback_finished = None, cover_file = None):
        if callback_status != None:
            callback_status( _('Downloading channel cover...'))
        pixbuf = PixbufLoader()
        
        if cover_file == None:
            if isDebugging():
                print "directly downloading %s" % url
            pixbuf.write( urllib.urlopen(url).read())
        
        if cover_file != None and not exists( cover_file):
            if isDebugging():
                print "downloading cover to %s" % cover_file
            cachefile = open( cover_file, "w")
            cachefile.write( urllib.urlopen(url).read())
            cachefile.close()
        
        if cover_file != None:
            if isDebugging():
                print "reading cover from %s" % cover_file
            pixbuf.write( open( cover_file, "r").read())
        
        try:
            pixbuf.close()
        except:
            # data error, delete temp file
            self.deleteFilename( cover_file)
        
        if callback_pixbuf != None:
            callback_pixbuf( pixbuf.get_pixbuf())
        if callback_status != None:
            callback_status( '')
        if callback_finished != None:
            callback_finished()

    def get_image_from_url( self, url, callback_pixbuf = None, callback_status = None, callback_finished = None, cover_file = None):
        args = ( url, callback_pixbuf, callback_status, callback_finished, cover_file )
        thread = threading.Thread( target = self.image_download_thread, args = args)
        thread.start()

    def deleteFilename( self, filename):
        if isDebugging():
            print "deleteFilename: " + filename
        try:
            unlink( filename)
        except:
            # silently ignore 
            pass

class gPodderChannelWriter( object):
    def write( self, channels):
        filename = gPodderLib().getChannelsFilename()
        fd = open( filename, "w")
        print >> fd, '<!-- '+_('gPodder channel list')+' -->'
        print >> fd, '<channels>'
        for chan in channels:
            print >> fd, '  <channel name="%s">' % chan.filename
            print >> fd, '    <url>%s</url>' % saxutils.escape( chan.url)
            print >> fd, '    <download_dir>%s</download_dir>' % saxutils.escape( chan.save_dir)
            print >> fd, '  </channel>'
        print >> fd, '</channels>'
        fd.close()

class gPodderChannelReader( DefaultHandler):
    channels = []
    current_item = None
    current_element_data = ""

    def __init__( self):
        None
    
    def read( self, force_update = False):
        self.channels = []
        parser = make_parser()
        parser.setContentHandler( self)
        if exists( gPodderLib().getChannelsFilename()):
            parser.parse( gPodderLib().getChannelsFilename())
        else:
            return []
        reader = rssReader()
        input_channels = []
        
        for channel in self.channels:
            cachefile = channel.downloadRss(force_update)
            # check if download was a success
            if cachefile != None:
                reader.parseXML(channel.url, cachefile)
            
                if channel.filename != "" and channel.filename != "__unknown__":
                    reader.channel.shortname = channel.filename
            
                input_channels.append( reader.channel)
        
        return input_channels
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        if name == "channel":
            self.current_item = podcastChannel()
            self.current_item.filename = attrs.get( "name", "")
    
    def endElement( self, name):
        if self.current_item != None:
            if name == "url":
                self.current_item.url = self.current_element_data
            if name == "download_dir":
                self.current_item.download_dir = self.current_element_data
            if name == "channel":
                self.channels.append( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


