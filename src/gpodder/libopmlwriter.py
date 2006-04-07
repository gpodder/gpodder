
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
#  libopmlwriter.py -- opml output writer for exports
#  thomas perl <thp@perli.net>   20051208
#
#

from datetime import datetime

from libpodcasts import podcastChannel

class opmlWriter( object):
    ofile = None
    
    def __init__( self, filename):
        self.ofile = open( filename, "w")
	self.ofile.write( '<?xml version="1.0" encoding="ISO-8859-1"?>'+"\n")
	self.ofile.write( '<opml version="1.1">'+"\n")
	self.ofile.write( '<head>'+"\n")
	self.ofile.write( '<title>'+_('gPodder subscription list (exported)')+'</title>'+"\n")
	self.ofile.write( '<dateCreated>' + datetime.now().ctime() + '</dateCreated>'+"\n")
	self.ofile.write( '</head>'+"\n")
	self.ofile.write( '<body>'+"\n")

    def close( self):
        self.ofile.write( '</body>'+"\n")
        self.ofile.write( '</opml>'+"\n")
        self.ofile.close()

    def addChannel( self, channel):
        self.ofile.write( '<outline text="' + channel.title + '" title="' + channel.title + '" type="rss" xmlUrl="' + channel.url + '"/>'+"\n")

