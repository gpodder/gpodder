# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

import os
import gtk
import gtk.gdk
import fnmatch
import threading

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder.liblogger import log

from gpodder.gtkui.interface.common import BuilderWidget

class gPodderDevicePlaylist(BuilderWidget):
    finger_friendly_widgets = ['btnCancelPlaylist', 'btnSavePlaylist', 'treeviewPlaylist']

    def new(self):
        self.linebreak = '\n'
        if self._config.mp3_player_playlist_win_path:
            self.linebreak = '\r\n'
        self.mountpoint = util.find_mount_point(self._config.mp3_player_folder)
        if self.mountpoint == '/':
            self.mountpoint = self._config.mp3_player_folder
            log('Warning: MP3 player resides on / - using %s as MP3 player root', self.mountpoint, sender=self)
        self.playlist_file = os.path.join(self.mountpoint,
                                          self._config.mp3_player_playlist_file)
        icon_theme = gtk.icon_theme_get_default()
        self.icon_new = icon_theme.load_icon(gtk.STOCK_NEW, 16, 0)

        # add column two
        check_cell = gtk.CellRendererToggle()
        check_cell.set_property('activatable', True)
        check_cell.connect('toggled', self.cell_toggled)
        check_column = gtk.TreeViewColumn(_('Use'), check_cell, active=1)
        self.treeviewPlaylist.append_column(check_column)

        # add column three
        column = gtk.TreeViewColumn(_('Filename'))
        icon_cell = gtk.CellRendererPixbuf()
        column.pack_start(icon_cell, False)
        column.add_attribute(icon_cell, 'pixbuf', 0)
        filename_cell = gtk.CellRendererText()
        column.pack_start(filename_cell, True)
        column.add_attribute(filename_cell, 'text', 2)

        column.set_resizable(True)
        self.treeviewPlaylist.append_column(column)

        # Make treeview reorderable
        self.treeviewPlaylist.set_reorderable(True)

        # init liststore
        self.playlist = gtk.ListStore(gtk.gdk.Pixbuf, bool, str)
        self.treeviewPlaylist.set_model(self.playlist)

        # read device and playlist and fill the TreeView
        title = _('Reading files from %s') % self._config.mp3_player_folder
        message = _('Please wait your media file list is being read from device.')
        dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE)
        dlg.set_title(title)
        dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))
        dlg.show_all()
        threading.Thread(target=self.process_device, args=[dlg]).start()

    def process_device(self, dlg):
        self.m3u = self.read_m3u()
        self.device = self.read_device()
        util.idle_add(self.write2gui, dlg)

    def cell_toggled(self, cellrenderertoggle, path):
        (treeview, liststore) = (self.treeviewPlaylist, self.playlist)
        it = liststore.get_iter(path)
        liststore.set_value(it, 1, not liststore.get_value(it, 1))

    def on_btnCancelPlaylist_clicked(self, widget):
        self.gPodderDevicePlaylist.destroy()

    def on_btnSavePlaylist_clicked(self, widget):
        self.write_m3u()
        self.gPodderDevicePlaylist.destroy()

    def read_m3u(self):
        """
        read all files from the existing playlist
        """
        tracks = []
        log("Read data from the playlistfile %s" % self.playlist_file)
        if os.path.exists(self.playlist_file):
            for line in open(self.playlist_file, 'r'):
                if not line.startswith('#EXT'):
                    if line.startswith('#'):
                        tracks.append([False, line[1:].strip()])
                    else:
                        tracks.append([True, line.strip()])
        return tracks

    def build_extinf(self, filename):
        if self._config.mp3_player_playlist_win_path:
            filename = filename.replace('\\', os.sep)

        # rebuild the whole filename including the mountpoint
        if self._config.mp3_player_playlist_absolute_path:
            absfile = self.mountpoint + filename
        else:
            absfile = util.rel2abs(filename, os.path.dirname(self.playlist_file))

        # fallback: use the basename of the file
        (title, extension) = os.path.splitext(os.path.basename(filename))

        return "#EXTINF:0,%s%s" % (title.strip(), self.linebreak)

    def write_m3u(self):
        """
        write the list into the playlist on the device
        """
        log('Writing playlist file: %s', self.playlist_file, sender=self)
        playlist_folder = os.path.split(self.playlist_file)[0]
        if not util.make_directory(playlist_folder):
            self.show_message(_('Folder %s could not be created.') % playlist_folder, _('Error writing playlist'))
        else:
            try:
                fp = open(self.playlist_file, 'w')
                fp.write('#EXTM3U%s' % self.linebreak)
                for icon, checked, filename in self.playlist:
                    fp.write(self.build_extinf(filename))
                    if not checked:
                        fp.write('#')
                    fp.write(filename)
                    fp.write(self.linebreak)
                fp.close()
                self.show_message(_('The playlist on your MP3 player has been updated.'), _('Update successful'))
            except IOError, ioe:
                self.show_message(str(ioe), _('Error writing playlist file'))

    def read_device(self):
        """
        read all files from the device
        """
        log('Reading files from %s', self._config.mp3_player_folder, sender=self)
        tracks = []
        for root, dirs, files in os.walk(self._config.mp3_player_folder):
            for file in files:
                filename = os.path.join(root, file)

                if filename == self.playlist_file or fnmatch.fnmatch(filename, '*.dat') or fnmatch.fnmatch(filename, '*.DAT'):
                    # We don't want to have our playlist file as
                    # an entry in our file list, so skip it!
                    # We also don't want to include dat files
                    continue

                if self._config.mp3_player_playlist_absolute_path:
                    filename = filename[len(self.mountpoint):]
                else:
                    filename = util.relpath(os.path.dirname(self.playlist_file),
                                            os.path.dirname(filename)) + \
                               os.sep + os.path.basename(filename)

                if self._config.mp3_player_playlist_win_path:
                    filename = filename.replace(os.sep, '\\')

                tracks.append(filename)
        return tracks

    def write2gui(self, dlg):
        # add the files from the device to the list only when
        # they are not yet in the playlist
        # mark this files as NEW
        for filename in self.device[:]:
            m3ulist = [file[1] for file in self.m3u]
            if filename not in m3ulist:
                self.playlist.append([self.icon_new, False, filename])

        # add the files from the playlist to the list only when
        # they are on the device
        for checked, filename in self.m3u[:]:
            if filename in self.device:
                self.playlist.append([None, checked, filename])

        dlg.destroy()
        return False

