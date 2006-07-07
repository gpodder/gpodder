
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
#  libopmlreader.py -- opml ("podcast list") reader functionality
#  thomas perl <thp@perli.net>   20060613
#
#

import gtk
import gobject

import libgpodder

from xml.sax.saxutils import DefaultHandler
from xml.sax.handler import ErrorHandler
from xml.sax import make_parser
from string import strip

from urllib import unquote_plus

from libpodcasts import opmlChannel
from libpodcasts import stripHtml

from librssreader import rssErrorHandler


class opmlReader( DefaultHandler):
    channels = []
    title = 'Unknown OPML Channel'
    
    current_item = None
    current_element_data = ""

    def __init__( self):
        None

    def get_model( self):
        new_model = gtk.ListStore( gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING)
        
        for channel in self.channels:
            new_iter = new_model.append()
            new_model.set( new_iter, 0, False)
            new_model.set( new_iter, 1, channel.title)
            new_model.set( new_iter, 2, channel.xmlurl)
        
        return new_model
    
    def parseXML( self, filename):
        self.channels = []
        parser = make_parser()
	parser.returns_unicode = True
        parser.setContentHandler( self)
	parser.setErrorHandler( rssErrorHandler())
        # no multithreaded access to filename
        libgpodder.getLock()
        try:
            parser.parse( filename)
        finally:
            libgpodder.releaseLock()
    
    def startElement( self, name, attrs):
        self.current_element_data = ""
        
        otype = attrs.get( 'type', '???')
        xmlurl = attrs.get( 'xmlUrl', '')
        title = attrs.get( 'title', '')

        # in case the title is not set, use text (example: odeo.com)
        if title == '':
            title = unquote_plus( attrs.get( 'text', ''))
            # if still not found (what the..?), use URL
            if title == '':
                title = 'Unknown (%s)' % ( xmlurl )

        # otype = 'link' to support odeo.com feeds
        if name == 'outline' and (otype == 'rss' or otype == 'link') and xmlurl != '':
            self.channels.append( opmlChannel( xmlurl, title))
    
    def endElement( self, name):
        if name == 'title':
            self.title = self.current_element_data
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch


