# -*- coding: utf-8 -*-
#
# gpodder.opml: OPML import and export functionality (2007-08-19)
# Copyright (c) 2007-2013, Thomas Perl <m@thp.io>
#
# Based on:
# libopmlreader.py (2006-06-13)
# libopmlwriter.py (2005-12-08)
# Copyright (c) 2005-2007 Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#


"""OPML import and export functionality

This module contains helper classes to import subscriptions 
from OPML files on the web and to export a list of channel 
objects to valid OPML 1.1 files that can be used to backup 
or distribute gPodder's channel subscriptions.
"""

import logging
logger = logging.getLogger(__name__)

from gpodder import util

import xml.dom.minidom

import os.path
import os
import shutil

from email.utils import formatdate
import gpodder


class Importer(object):
    """
    Helper class to import an OPML feed from protocols
    supported by urllib2 (e.g. HTTP) and return a GTK 
    ListStore that can be displayed in the GUI.

    This class should support standard OPML feeds and
    contains workarounds to support odeo.com feeds.
    """

    VALID_TYPES = ('rss', 'link')

    def __init__( self, url):
        """
        Parses the OPML feed from the given URL into 
        a local data structure containing channel metadata.
        """
        self.items = []
        try:
            if os.path.exists(url):
                doc = xml.dom.minidom.parse(url)
            else:
                doc = xml.dom.minidom.parseString(util.urlopen(url).read())

            for outline in doc.getElementsByTagName('outline'):
                # Make sure we are dealing with a valid link type (ignore case)
                otl_type = outline.getAttribute('type')
                if otl_type is None or otl_type.lower() not in self.VALID_TYPES:
                    continue

                if outline.getAttribute('xmlUrl') or outline.getAttribute('url'):
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
                logger.info('OPML import finished, but no items found: %s', url)
        except:
            logger.error('Cannot import OPML from URL: %s', url, exc_info=True)



class Exporter(object):
    """
    Helper class to export a list of channel objects
    to a local file in OPML 1.1 format.

    See www.opml.org for the OPML specification.
    """

    FEED_TYPE = 'rss'

    def __init__( self, filename):
        if filename is None:
            self.filename = None
        elif filename.endswith( '.opml') or filename.endswith( '.xml'):
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

        OPML 2.0 specification: http://www.opml.org/spec2

        Returns True on success or False when there was an 
        error writing the file.
        """
        if self.filename is None:
            return False

        doc = xml.dom.minidom.Document()

        opml = doc.createElement('opml')
        opml.setAttribute('version', '2.0')
        doc.appendChild(opml)

        head = doc.createElement( 'head')
        head.appendChild( self.create_node( doc, 'title', 'gPodder subscriptions'))
        head.appendChild( self.create_node( doc, 'dateCreated', formatdate(localtime=True)))
        opml.appendChild( head)

        body = doc.createElement( 'body')
        for channel in channels:
            body.appendChild( self.create_outline( doc, channel))
        opml.appendChild( body)

        try:
            with util.update_file_safely(self.filename) as temp_filename:
                with open(temp_filename, 'w') as fp:
                    fp.write(doc.toprettyxml(indent='  ', newl=os.linesep))
        except:
            logger.error('Could not open file for writing: %s',
                    self.filename, exc_info=True)
            return False

        return True

