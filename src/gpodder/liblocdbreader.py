

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

from liblogger import log

class rssLocDBErrorHandler( ErrorHandler):
    def __init__( self):
        pass

    def error( self, exception):
        log( 'Local DB reader error: %s', str(exception))

    def fatalError( self, exception):
        log( 'Local DB reader fatal error: %s', str(exception))

    def warning( self, exception):
        log( 'Local DB reader warning: %s', str(exception))

class readLocalDB( DefaultHandler):
    def __init__( self, url):
        self.url = url
        self.channel = None
        self.current_item = None
        self.current_element_data = ""
        self.filename = None
    
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
            self.channel = libpodcasts.podcastChannel( url = self.url)
        if name == "item":
            self.current_item = libpodcasts.podcastItem( self.channel)
        if name == "gpodder:info" and self.channel != None and self.current_item == None:
            self.channel.device_playlist_name = attrs.get('playlist', 'gPodder')
            if attrs.get('music', 'false').lower() == 'true':
                self.channel.is_music_channel = True
            if attrs.get('nosync', 'false').lower() == 'true':
                self.channel.sync_to_devices = False
            self.channel.override_title = attrs.get('title','')
            self.channel.username = attrs.get('username', '')
            self.channel.password = self.channel.obfuscate_password(attrs.get('password', ''), unobfuscate = True)
    
    def endElement( self, name):
        if self.current_item == None:
            if name == "title":
                self.channel.title = self.current_element_data
            if name == "link":
                self.channel.link = self.current_element_data
            if name == "description":
                self.channel.description = self.current_element_data
            if name == "pubDate":
                self.channel.pubDate = self.current_element_data
            if name == "copyright":
                self.channel.copyright = self.current_element_data
            if name == "webMaster":
                self.channel.webMaster = self.current_element_data
        
        if self.current_item != None:
            if name == "title":
                self.current_item.title = self.current_element_data
            if name == "url":
                self.current_item.url = self.current_element_data
            if name == "description":
                self.current_item.description = self.current_element_data
            if name == "link":
                self.current_item.link = self.current_element_data
            if name == "guid":
                self.current_item.guid = self.current_element_data
            if name == "pubDate":
                self.current_item.pubDate = self.current_element_data
            if name == "mimeType":
                self.current_item.mimetype = self.current_element_data
            if name == "item":
                self.current_item.calculate_filesize()
                self.channel.append( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


