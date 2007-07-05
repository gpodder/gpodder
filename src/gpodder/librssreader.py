
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
#  librssreader.py -- xml reader functionality
#  thomas perl <thp@perli.net>   20051029
#
#

import libgpodder

from xml.sax.saxutils import DefaultHandler
from xml.sax.handler import ErrorHandler
from xml.sax import make_parser
from string import strip

from libpodcasts import podcastChannel
from libpodcasts import podcastItem
from libpodcasts import stripHtml

from liblogger import log

class rssReader( DefaultHandler, ErrorHandler):
    def __init__( self):
        self.channel_url = ''
        self.channel = None
        self.current_item = None
        self.current_element_data = ''
        self.parse_tree = []
    
    def error( self, exception):
        log( '[rssReader] Error: %s', str( exception))
        log( 'Disposing channel: %s', self.channel_url)
        self.channel = None

    def fatalError( self, exception):
        log( '[rssReader] Fatal Error: %s', str( exception))
        log( 'Disposing channel: %s', self.channel_url)
        self.channel = None

    def warning( self, exception):
        log( '[rssReader] Warning: %s', str( exception))

    def parseXML( self, url, filename):
        self.channel_url = url
        self.channel = None
        self.current_item = None
        self.current_element_data = ''
        self.parse_tree = []
        parser = make_parser()
	parser.returns_unicode = True
        parser.setContentHandler( self)
	parser.setErrorHandler( self)
        # no multithreaded access to filename
        libgpodder.getLock()
        try:
            parser.parse( filename)
        finally:
            libgpodder.releaseLock()

        if self.channel and self.channel.can_sort_by_pubdate():
            # All episodes have a parseable pubDate, so 
            # we can simply sort the episodes by their 
            # pubDate and be sure to have a sane ordering.
            self.channel.sort( reverse = True)

        if self.channel and not self.channel.description:
            self.channel.description = self.channel.url
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        self.parse_tree.append( name)

        if name == "channel":
            self.channel = podcastChannel( self.channel_url)

        if name == "item":
            self.current_item = podcastItem()
        
        if name == "enclosure" and self.current_item:
            self.current_item.url = attrs.get( "url", "")
            self.current_item.length = attrs.get( "length", "")
            self.current_item.mimetype = attrs.get( "type", "")

        if name == "itunes:image" and self.channel != None:
            self.channel.image = attrs.get( "href", "")
    
    def endElement( self, name):
        self.parse_tree.pop()

        if self.channel != None and not self.current_item and len(self.parse_tree) and self.parse_tree[-1] == 'channel':
            if name == "title":
                self.channel.title = self.current_element_data
            if name == "link":
                self.channel.link = self.current_element_data
            if name == "description":
                self.channel.description = stripHtml( self.current_element_data)
            if name == "pubDate":
                self.channel.pubDate = self.current_element_data
            if name == "language":
                self.channel.language = self.current_element_data
            if name == "copyright":
                self.channel.copyright = self.current_element_data
            if name == "webMaster":
                self.channel.webMaster = self.current_element_data
        
        if self.channel != None and self.current_item:
            if name == "title":
                self.current_item.title = self.current_element_data
            if name == "link":
                self.current_item.link = self.current_element_data
            if name == "description":
                self.current_item.description = stripHtml( self.current_element_data)
            if name == "guid":
                self.current_item.guid = self.current_element_data
            if name == "pubDate":
                self.current_item.pubDate = self.current_element_data
            if name == "item":
                if self.current_item.url:
                    if not self.current_item.title:
                        self.current_item.title = self.current_item.description.strip().split('\n')[0].strip()
                    self.channel.append( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


