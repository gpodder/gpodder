
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

from xml.sax.saxutils import DefaultHandler
from xml.sax import make_parser
from string import strip
from os.path import expanduser
from os.path import basename
from os.path import exists
from os.path import dirname
from os import mkdir
from threading import Event

from libpodcasts import configChannel
from librssreader import rssReader
from libwget import downloadThread

# global debugging variable, set to False on release
debugging = True

def isDebugging():
    return debugging

class gPodderLib( object):
    gpodderdir = ""
    downloaddir = ""
    cachedir = ""
    
    def __init__( self):
        self.gpodderdir = expanduser( "~/.config/gpodder/")
        self.createIfNecessary( self.gpodderdir)
        self.downloaddir = self.gpodderdir + "downloads/"
        self.createIfNecessary( self.downloaddir)
        self.cachedir = self.gpodderdir + "cache/"
        self.createIfNecessary( self.cachedir)
    
    def createIfNecessary( self, path):
        #TODO: recursive mkdir all parent directories
	
        if path.endswith('/'):
            path = path[:-1]
	
        if not exists(dirname(path)):
            mkdir(dirname(path))
	
        if not exists( path):
            mkdir( path)
    
    def getConfigFilename( self):
        return self.gpodderdir + "gpodder.conf.xml"
    
    def getChannelsFilename( self):
        return self.gpodderdir + "channels.xml"
    
    def getChannelSaveDir( self, filename):
        savedir = self.downloaddir + filename + "/"
        self.createIfNecessary( savedir)
        
        return savedir
    
    def getChannelCacheFile( self, filename):
        return self.cachedir + filename + ".xml"
    
    def getPodcastFilename( self, channel, url):
        # strip question mark (and everything behind it), fix %20 errors
        filename = basename( url).replace( "%20", " ")
	indexOfQuestionMark = filename.rfind( "?")
	if indexOfQuestionMark != -1:
	    filename = filename[:indexOfQuestionMark]
	# end strip questionmark
        return self.getChannelSaveDir( configChannel( channel.title).filename) + filename

    def podcastFilenameExists( self, channel, url):
        return exists( self.getPodcastFilename( channel, url))
    
    def downloadRss( self, channel_url, channel_filename = "__unknown__", force_update = True):
        if channel_filename == "":
            channel_filename = "__unknown__"
        
        cachefile = gPodderLib().getChannelCacheFile( channel_filename)
        
        if (channel_filename == "__unknown__" or exists( cachefile) == False) or force_update:
            event = Event()
            downloadThread( channel_url, cachefile, event).download()
            
            while event.isSet() == False:
                event.wait( 0.2)
                while gtk.events_pending():
                    gtk.main_iteration( False)
        
        return cachefile



class gPodderChannelWriter( object):
    def __init__( self):
        None
    
    def write( self, channels):
        filename = gPodderLib().getChannelsFilename()
        fd = open( filename, "w")
        fd.write( "<!-- automatically generated, will be overwritten on next gpodder shutdown.-->\n")
        fd.write( "<channels>\n")
        for chan in channels:
            configch = configChannel( chan.title, chan.url, chan.shortname)
            fd.write( "  <channel name=\"" + configch.filename + "\">\n")
            fd.write( "    <url>" + configch.url + "</url>\n")
            fd.write( "  </channel>\n")
        fd.write( "</channels>\n")
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
            cachefile = gPodderLib().downloadRss( channel.url, channel.filename, force_update)
            reader.parseXML( channel.url, cachefile)
            
            if channel.filename != "" and channel.filename != "__unknown__":
                reader.channel.shortname = channel.filename
            
            input_channels.append( reader.channel)
        
        return input_channels
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        if name == "channel":
            self.current_item = configChannel()
            self.current_item.filename = attrs.get( "name", "")
    
    def endElement( self, name):
        if self.current_item != None:
            if name == "url":
                self.current_item.url = self.current_element_data
            if name == "channel":
                self.channels.append( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


