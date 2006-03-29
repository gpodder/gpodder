
#
# gPodder
# Copyright (c) 2005 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
#

#
#  libgpodder.py -- gpodder configuration
#  thomas perl <thp@perli.net>   20051030
#
#

import gtk
import thread
import threading

from xml.sax.saxutils import DefaultHandler
from xml.sax import make_parser
from string import strip
from os.path import expanduser
from os.path import exists
from os.path import dirname
from os import mkdir
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

# global debugging variable, set to False on release
# TODO: while developing a new version, set this to "True"
debugging = False

# global recursive lock for thread exclusion
globalLock = threading.RLock()

def isDebugging():
    return debugging

def getLock():
    globalLock.acquire()

def releaseLock():
    globalLock.release()

class gPodderLib( object):
    gpodderdir = ""
    downloaddir = ""
    cachedir = ""
    http_proxy = ""
    ftp_proxy = ""
    open_app = ""
    
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
        #TODO: recursive mkdir all parent directories
	
        if path.endswith('/'):
            path = path[:-1]
	
        if not exists(dirname(path)):
            mkdir(dirname(path))
	
        if not exists( path):
            mkdir( path)
    
    def getConfigFilename( self):
        return self.gpodderdir + "gpodder.conf"
    
    def getChannelsFilename( self):
        return self.gpodderdir + "channels.xml"

    def propertiesChanged( self):
        # set new environment variables for subprocesses to use
        environ['http_proxy'] = self.http_proxy
        environ['ftp_proxy'] = self.ftp_proxy
        # save settings for next startup
        self.saveConfig()

    def saveConfig( self):
        fn = self.getConfigFilename()
        fp = open( fn, "w")
        fp.write( self.http_proxy + "\n")
        fp.write( self.ftp_proxy + "\n")
        fp.write( self.open_app + "\n")
        fp.close()
    
    def loadConfig( self):
        try:
            fn = self.getConfigFilename()
            fp = open( fn, "r")
            http = fp.readline()
            ftp = fp.readline()
            app = fp.readline()
            if http != "" and ftp != "":
                self.http_proxy = strip( http)
                self.ftp_proxy = strip( ftp)
            if strip( app) != "":
                self.open_app = strip( app)
            else:
                self.open_app = "gnome-open"
            fp.close()
        except:
            # TODO: well, well.. (http + ftp?)
            self.open_app = "gnome-open"

    def openFilename( self, filename):
        if isDebugging():
            print "open " + filename + " with " + self.open_app
        system( self.open_app + " " + filename + " &")

    def getDesktopSymlink( self):
        symlink_path = expanduser( "~/Desktop/gPodder downloads")
        return exists( symlink_path)

    def createDesktopSymlink( self):
        if isDebugging():
            print "createDesktopSymlink requested"
        if not self.getDesktopSymlink():
            downloads_path = expanduser( "~/Desktop/")
            self.createIfNecessary( downloads_path)
            symlink( self.downloaddir, downloads_path + "gPodder downloads")
    
    def removeDesktopSymlink( self):
        if isDebugging():
            print "removeDesktopSymlink requested"
        if self.getDesktopSymlink():
            unlink( expanduser( "~/Desktop/gPodder downloads"))

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
        print >> fd, '<!-- automatically generated, will be overwritten on next gpodder shutdown.-->'
        print >> fd, '<channels>'
        for chan in channels:
            print >> fd, '  <channel name="%s">' %chan.filename
            print >> fd, '    <url>%s</url>' %chan.url
            print >> fd, '    <download_dir>%s</download_dir>' %chan.save_dir
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


