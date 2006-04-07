

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
        # no multithread access to filename
        libgpodder.getLock()
        try:
            parser.parse( filename)
        finally:
            libgpodder.releaseLock()
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        if name == "channel":
            # no "real" url needed for podcastChannel, because we only use it as a container
            self.channel = libpodcasts.podcastChannel( self.filename)
        if name == "item":
            self.current_item = libpodcasts.podcastItem()
        if name == "gpodder:info" and self.channel != None:
            if attrs.get('nosync', 'false').lower() == 'true':
                if libgpodder.isDebugging():
                    print 'local channel does not want to be synced: %s' % self.channel.title
                self.channel.sync_to_devices = False
    
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
                # this produces lots of output and works ATM, so output disabled
                if libgpodder.isDebugging() and False:
                    print "importing local db channel: " + self.current_item.url
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


