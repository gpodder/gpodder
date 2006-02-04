
#
# gPodder
# Copyright (c) 2005-2006 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
#

#
#  liblocdbreader.py -- xml reader functionality
#  thomas perl <thp@perli.net>   20060110
#
#

from xml.sax.saxutils import DefaultHandler
from xml.sax.handler import ErrorHandler
from xml.sax import make_parser
from string import strip

import libpodcasts
import libgpodder

class rssLocDBErrorHandler( ErrorHandler):
    def __init__( self):
        None

    def error( self, exception):
        print exception

    def fatalError( self, exception):
        print "FATAL ERROR: ", exception

    def warning( self, exception):
        print "warning: ", exception

class readLocalDB( DefaultHandler):
    channel = None
    current_item = None
    current_element_data = ""
    filename = None

    def __init__( self):
        None
    
    def parseXML( self, filename):
        self.filename = filename
        parser = make_parser()
	parser.returns_unicode = True
        parser.setContentHandler( self)
	parser.setErrorHandler( rssLocDBErrorHandler())
        parser.parse( filename)
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        if name == "channel":
            # no "real" url needed for podcastChannel, because we only use it as a container
            self.channel = libpodcasts.podcastChannel( self.filename)
        if name == "item":
            self.current_item = libpodcasts.podcastItem()
    
    def endElement( self, name):
        if self.current_item == None:
            if name == "title":
                self.channel.title = self.current_element_data
            if name == "link":
                self.channel.link = self.current_element_data
            if name == "description":
                self.channel.description = self.current_element_data
        
        if self.current_item != None:
            if name == "title":
                self.current_item.title = self.current_element_data
            if name == "url":
                self.current_item.url = self.current_element_data
            if name == "description":
                self.current_item.description = self.current_element_data
            if name == "item":
                self.channel.addItem( self.current_item)
                if libgpodder.isDebugging():
                    print "importing local db channel: " + self.current_item.url
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


