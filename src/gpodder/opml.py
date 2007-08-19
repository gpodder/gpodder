
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
#  opml.py -- OPML import and export functionality
#  Thomas Perl <thp@perli.net>   2007-08-19
#
#  based on: libopmlreader.py (2006-06-13)
#            libopmlwriter.py (2005-12-08)
#

"""OPML import and export functionality

This module contains helper classes to import subscriptions 
from OPML files on the web and to export a list of channel 
objects to valid OPML 1.1 files that can be used to backup 
or distribute gPodder's channel subscriptions.
"""

from gpodder.liblogger import log

import gtk
import gobject

import xml.dom.minidom
import xml.sax.saxutils

import urllib
import urllib2

import datetime


class Importer(object):
    """
    Helper class to import an OPML feed from protocols
    supported by urllib2 (e.g. HTTP) and return a GTK 
    ListStore that can be displayed in the GUI.

    This class should support standard OPML feeds and
    contains workarounds to support odeo.com feeds.
    """

    VALID_TYPES = ( 'rss', 'link' )

    def __init__( self, url):
        """
        Parses the OPML feed from the given URL into 
        a local data structure containing channel metadata.
        """
        self.items = []
        try:
            doc = xml.dom.minidom.parseString( urllib2.urlopen( url).read())
            for outline in doc.getElementsByTagName('outline'):
                if outline.getAttribute('type') in self.VALID_TYPES and outline.getAttribute('xmlUrl'):
                    channel = {
                        'url': outline.getAttribute('xmlUrl'),
                        'title': outline.getAttribute('title') or outline.getAttribute('text') or outline.getAttribute('xmlUrl'),
                        'description': outline.getAttribute('text') or outline.getAttribute('xmlUrl'),
                    }

                    if channel['description'] == channel['title']:
                        channel['description'] = channel['url']

                    for attr in ( 'url', 'title', 'description' ):
                        channel[attr] = channel[attr].strip()

                    self.items.append( channel)
            if not len(self.items):
                log( 'OPML import finished, but no items found: %s', url, sender = self)
        except:
            log( 'Cannot import OPML from URL: %s', url, sender = self)

    def format_channel( self, channel):
        """
        Formats a channel dictionary (as populated by the 
        constructor) into a Pango markup string, suitable 
        for output in GTK widgets.

        The resulting string contains the title and description.
        """
        return '<b>%s</b>\n<span size="small">%s</span>' % ( xml.sax.saxutils.escape( urllib.unquote_plus( channel['title'])), xml.sax.saxutils.escape( channel['description']), )

    def get_model( self):
        """
        Returns a gtk.ListStore with three columns:

         - a bool that is initally set to False
         - a descriptive Pango markup string created
           by calling self.format_channel()
         - the URL of the channel as string
        """
        model = gtk.ListStore( gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING)

        for channel in self.items:
            model.append( [ False, self.format_channel( channel), channel['url'] ])

        return model



class Exporter(object):
    """
    Helper class to export a list of channel objects
    to a local file in OPML 1.1 format.

    See www.opml.org for the OPML specification.
    """

    FEED_TYPE = 'rss'

    def __init__( self, filename):
        if filename.endswith( '.opml') or filename.endswith( '.xml'):
            self.filename = filename
        else:
            self.filename = '%s.opml' % ( filename, )

    def create_node( self, doc, name, content):
        """
        Creates a simple XML Element node in a document 
        with tag name "name" and text content "content", 
        as in <name>content</name> and returns the element.
        """
        node = doc.createElement( name)
        node.appendChild( doc.createTextNode( content))
        return node

    def create_outline( self, doc, channel):
        """
        Creates a OPML outline as XML Element node in a
        document for the supplied channel.
        """
        outline = doc.createElement( 'outline')
        outline.setAttribute( 'text', channel.title)
        outline.setAttribute( 'title', channel.title)
        outline.setAttribute( 'xmlUrl', channel.url)
        outline.setAttribute( 'type', self.FEED_TYPE)
        return outline

    def write( self, channels):
        """
        Creates a XML document containing metadata for each 
        channel object in the "channels" parameter, which 
        should be a list of channel objects.

        Returns True on success or False when there was an 
        error writing the file.
        """
        doc = xml.dom.minidom.Document()

        opml = doc.createElement( 'opml')
        opml.setAttribute( 'version', '1.1')
        doc.appendChild( opml)

        head = doc.createElement( 'head')
        head.appendChild( self.create_node( doc, 'title', 'gPodder subscriptions'))
        head.appendChild( self.create_node( doc, 'dateCreated', datetime.datetime.now().ctime()))
        opml.appendChild( head)

        body = doc.createElement( 'body')
        for channel in channels:
            body.appendChild( self.create_outline( doc, channel))
        opml.appendChild( body)

        try:
            fp = open( self.filename, 'w')
            fp.write( doc.toxml( encoding = 'utf-8'))
            fp.close()
        except:
            log( 'Could not open file for writing: %s', self.filename, sender = self)
            return False

        return True

