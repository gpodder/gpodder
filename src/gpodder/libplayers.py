
#
# gPodder
# Copyright (c) 2005 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
#

#
#  libplayers.py -- get list of potential playback apps
#  thomas perl <thp@perli.net>   20060329
#
#

from os import listdir
from os.path import basename
from os.path import splitext
from os.path import exists

from ConfigParser import RawConfigParser

import gobject

from gtk import IconTheme
from gtk import ListStore

from gtk.gdk import pixbuf_new_from_file_at_size
from gtk.gdk import Pixbuf

import libgpodder

# where are the .desktop files located?
userappsdir = '/usr/share/applications/'

# the name of the section in the .desktop files
sect = 'Desktop Entry'

class UserApplication(object):
    def __init__( self, name, cmd, mime, icon):
        self.name = name
        self.cmd = cmd
        self.icon = icon
        self.theme = IconTheme()

    def get_icon( self):
        if self.icon != None:
            if exists( self.icon):
                return pixbuf_new_from_file_at_size( self.icon, 24, 24)
            icon_name = splitext( basename( self.icon))[0]
            if self.theme.has_icon( icon_name):
                return self.theme.load_icon( icon_name, 24, 0)

    def get_name( self):
        return self.name

    def get_action( self):
        return self.cmd


class UserAppsReader(object):
    def __init__( self):
        self.apps = []

    def read( self):
        files = listdir( userappsdir)
        for file in files:
            self.parse_and_append( file)
        self.apps.append( UserApplication( 'Shell command', '', 'audio/*', 'gtk-execute'))

    def parse_and_append( self, filename):
        parser = RawConfigParser()
        parser.read( [ userappsdir + filename ])
        if not parser.has_section( sect):
            return
        
        try:
            app_name = parser.get( sect, 'Name')
            app_cmd = parser.get( sect, 'Exec')
            app_mime = parser.get( sect, 'MimeType')
            app_icon = parser.get( sect, 'Icon')
            if app_mime.find( 'audio/') != -1:
                if libgpodder.isDebugging():
                    print "found app in " + userappsdir + filename + " ("+app_name+")"
                self.apps.append( UserApplication( app_name, app_cmd, app_mime, app_icon))
        except:
            return

    def get_applications_as_model( self):
        result = ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, Pixbuf)
        for app in self.apps:
            iter = result.append()
            result.set_value( iter, 0, app.get_name())
            result.set_value( iter, 1, app.get_action())
            result.set_value( iter, 2, app.get_icon())
        return result
# end of UserAppsReader

