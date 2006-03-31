
#
# gPodder
# Copyright (c) 2005 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
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

