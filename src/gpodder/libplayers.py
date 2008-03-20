# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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
#  libplayers.py -- get list of potential playback apps
#  thomas perl <thp@perli.net>   20060329
#
#

import glob
import os.path
import threading

from ConfigParser import RawConfigParser

import gobject
import gtk
import gtk.gdk

from gpodder.liblogger import log


# where are the .desktop files located?
userappsdirs = [ '/usr/share/applications/', '/usr/local/share/applications/', '/usr/share/applications/kde/' ]

# the name of the section in the .desktop files
sect = 'Desktop Entry'

class UserApplication(object):
    def __init__(self, name, cmd, mime, icon):
        self.name = name
        self.cmd = cmd
        self.icon = icon
        self.mime = mime

    def get_icon(self):
        if self.icon is not None:
            # Load it from an absolute filename
            if os.path.exists(self.icon):
                return gtk.gdk.pixbuf_new_from_file_at_size(self.icon, 24, 24)

            # Load it from the current icon theme
            (icon_name, extension) = os.path.splitext(os.path.basename(self.icon))
            theme = gtk.IconTheme()
            if theme.has_icon(icon_name):
                return theme.load_icon(icon_name, 24, 0)

    def is_mime(self, mimetype):
        return self.mime.find(mimetype+'/') != -1


class UserAppsReader(object):
    def __init__(self, mimetypes):
        self.apps = []
        self.mimetypes = mimetypes
        self.__model_cache = {}
        self.__has_read = False
        self.__finished = threading.Event()

    def read( self):
        if self.__has_read:
            return

        self.__has_read = True
        log('start reader', bench_start=True)
        for dir in userappsdirs:
            if os.path.exists( dir):
                for file in glob.glob(os.path.join(dir, '*.desktop')):
                    self.parse_and_append( file)
        log('end reader', bench_end=True)
        self.__finished.set()
        self.apps.append(UserApplication('Shell command', '', ';'.join((mime+'/*' for mime in self.mimetypes)), gtk.STOCK_EXECUTE))

    def parse_and_append( self, filename):
        try:
            parser = RawConfigParser()
            parser.read([filename])
            if not parser.has_section(sect):
                return
            
            # Find out if we need it by comparing mime types
            app_mime = parser.get(sect, 'MimeType')
            for needed_type in self.mimetypes:
                if app_mime.find(needed_type+'/') != -1:
                    log('Player found: %s', filename, sender=self)
                    app_name = parser.get(sect, 'Name')
                    app_cmd = parser.get(sect, 'Exec')
                    app_icon = parser.get(sect, 'Icon')
                    self.apps.append(UserApplication(app_name, app_cmd, app_mime, app_icon))
                    return
        except:
            return

    def get_applications_as_model(self, mimetype, return_model=True):
        self.__finished.wait()
        if mimetype not in self.__model_cache:
            result = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gtk.gdk.Pixbuf)
            for app in self.apps:
                if app.is_mime(mimetype):
                    result.append([app.name, app.cmd, app.get_icon()])
            self.__model_cache[mimetype] = result
        else:
            log('Using cached application list model for %s', mimetype, sender=self)

        if return_model:
            return self.__model_cache[mimetype]
        else:
            return False

