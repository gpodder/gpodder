# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

from gpodder import util

import gtk
import gobject

import xml.dom.minidom
import xml.sax.saxutils

import urllib
import urllib2
import os.path
import os

import datetime
import gpodder


class Importer(object):
    """
    Helper class to import an OPML feed from protocols
    supported by urllib2 (e.g. HTTP) and return a GTK 
    ListStore that can be displayed in the GUI.

    This class should support standard OPML feeds and
    contains workarounds to support odeo.com feeds.
    """

    VALID_TYPES = ( 'rss', 'link' )

    def read_url( self, url):
        request = urllib2.Request( url, headers = {'User-agent': gpodder.user_agent})
        return urllib2.urlopen( request).read()

    def __init__( self, url):
        """
        Parses the OPML feed from the given URL into 
        a local data structure containing channel metadata.
        """
        self.items = []
        try:
            if os.path.exists( url):
                # assume local filename
                doc = xml.dom.minidom.parse( url)
            else:
                doc = xml.dom.minidom.parseString( self.read_url( url))

            for outline in doc.getElementsByTagName('outline'):
                if outline.getAttribute('type') in self.VALID_TYPES and outline.getAttribute('xmlUrl') or outline.getAttribute('url'):
                    channel = {
                        'url': outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                        'title': outline.getAttribute('title') or outline.getAttribute('text') or outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                        'description': outline.getAttribute('text') or outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                    }

                    if channel['description'] == channel['title']:
                        channel['description'] = channel['url']

                    for attr in ( 'url', 'title', 'description' ):
                        channel[attr] = channel[attr].strip()

                    self.items.append( channel)
            if not len(self.items):
                log( 'OPML import finished, but no items found: %s', url, sender = self)
        except:
            log( 'Cannot import OPML from URL: %s', url, traceback=True, sender = self)

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
        outline.setAttribute( 'title', channel.title)
        outline.setAttribute( 'text', channel.description)
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
            data = doc.toprettyxml(encoding='utf-8', indent='    ', newl=os.linesep)
            # We want to have at least 512 KiB free disk space after
            # saving the opml data, if this is not possible, don't 
            # try to save the new file, but keep the old one so we
            # don't end up with a clobbed, empty opml file.
            FREE_DISK_SPACE_AFTER = 1024*512
            if util.get_free_disk_space(self.filename) < 2*len(data)+FREE_DISK_SPACE_AFTER:
                log('Not enough free disk space to save channel list to %s', self.filename, sender = self)
                return False
            fp = open(self.filename+'.tmp', 'w')
            fp.write(data)
            fp.close()
            os.rename(self.filename+'.tmp', self.filename)
        except:
            log( 'Could not open file for writing: %s', self.filename, sender = self)
            return False

        return True

