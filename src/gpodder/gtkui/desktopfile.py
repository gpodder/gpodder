# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

import gpodder

_ = gpodder.gettext

# where are the .desktop files located?
userappsdirs = [ '/usr/share/applications/', '/usr/local/share/applications/', '/usr/share/applications/kde/' ]

# the name of the section in the .desktop files
sect = 'Desktop Entry'

class PlayerListModel(gtk.ListStore):
    C_ICON, C_NAME, C_COMMAND, C_CUSTOM = range(4)

    def __init__(self):
        gtk.ListStore.__init__(self, gtk.gdk.Pixbuf, str, str, bool)

    def insert_app(self, pixbuf, name, command):
        self.append((pixbuf, name, command, False))

    def get_command(self, index):
        return self[index][self.C_COMMAND]

    def get_index(self, value):
        for index, row in enumerate(self):
            if value == row[self.C_COMMAND]:
                return index

        last_row = self[-1]
        name = _('Command: %s') % value
        if last_row[self.C_CUSTOM]:
            last_row[self.C_COMMAND] = value
            last_row[self.C_NAME] = name
        else:
            self.append((None, name, value, True))

        return len(self)-1

    @classmethod
    def is_separator(cls, model, iter):
        return model.get_value(iter, cls.C_COMMAND) == ''

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
                try:
                    return gtk.gdk.pixbuf_new_from_file_at_size(self.icon, 24, 24)
                except gobject.GError, ge:
                    pass

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
        self.__has_read = False
        self.__finished = threading.Event()
        self.__has_sep = False
        self.apps.append(UserApplication(_('Default application'), 'default', ';'.join((mime+'/*' for mime in self.mimetypes)), gtk.STOCK_OPEN))

    def add_separator(self):
        self.apps.append(UserApplication('', '', ';'.join((mime+'/*' for mime in self.mimetypes)), ''))
        self.__has_sep = True

    def read( self):
        if self.__has_read:
            return

        self.__has_read = True
        for dir in userappsdirs:
            if os.path.exists( dir):
                for file in glob.glob(os.path.join(dir, '*.desktop')):
                    self.parse_and_append( file)
        self.__finished.set()

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
                    app_name = parser.get(sect, 'Name')
                    app_cmd = parser.get(sect, 'Exec')
                    app_icon = parser.get(sect, 'Icon')
                    if not self.__has_sep:
                        self.add_separator()
                    self.apps.append(UserApplication(app_name, app_cmd, app_mime, app_icon))
                    return
        except:
            return

    def get_model(self, mimetype):
        self.__finished.wait()

        model = PlayerListModel()
        for app in self.apps:
            if app.is_mime(mimetype):
                model.insert_app(app.get_icon(), app.name, app.cmd)
        return model

