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
import pango
import urllib
import threading

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import opml
from gpodder import youtube

from gpodder.gtkui.opml import OpmlListModel

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderPodcastDirectory(BuilderWidget):
    finger_friendly_widgets = ['btnDownloadOpml', 'btnCancel', 'btnOK', 'treeviewChannelChooser']
    
    def new(self):
        if hasattr(self, 'custom_title'):
            self.gPodderPodcastDirectory.set_title(self.custom_title)

        if hasattr(self, 'hide_url_entry'):
            self.hboxOpmlUrlEntry.hide_all()
            new_parent = self.notebookChannelAdder.get_parent()
            new_parent.remove(self.notebookChannelAdder)
            self.vboxOpmlImport.reparent(new_parent)

        if not hasattr(self, 'add_urls_callback'):
            self.add_urls_callback = None

        self.setup_treeview(self.treeviewChannelChooser)
        self.setup_treeview(self.treeviewTopPodcastsChooser)
        self.setup_treeview(self.treeviewYouTubeChooser)

        self.notebookChannelAdder.connect('switch-page', lambda a, b, c: self.on_change_tab(c))

    def setup_treeview(self, tv):
        togglecell = gtk.CellRendererToggle()
        togglecell.set_property( 'activatable', True)
        togglecell.connect( 'toggled', self.callback_edited)
        togglecolumn = gtk.TreeViewColumn( '', togglecell, active=OpmlListModel.C_SELECTED)
        
        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn(_('Podcast'), titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)

        for itemcolumn in (togglecolumn, titlecolumn):
            tv.append_column(itemcolumn)

    def callback_edited( self, cell, path):
        model = self.get_treeview().get_model()
        model[path][OpmlListModel.C_SELECTED] = not model[path][OpmlListModel.C_SELECTED]
        self.btnOK.set_sensitive(bool(len(self.get_selected_channels())))

    def get_selected_channels(self, tab=None):
        channels = []

        model = self.get_treeview(tab).get_model()
        if model is not None:
            for row in model:
                if row[OpmlListModel.C_SELECTED]:
                    channels.append(row[OpmlListModel.C_URL])

        return channels

    def on_change_tab(self, tab):
        self.btnOK.set_sensitive( bool(len(self.get_selected_channels(tab))))

    def thread_finished(self, model, tab=0):
        if tab == 1:
            tv = self.treeviewTopPodcastsChooser
        elif tab == 2:
            tv = self.treeviewYouTubeChooser
            self.entryYoutubeSearch.set_sensitive(True)
            self.btnSearchYouTube.set_sensitive(True)
            self.btnOK.set_sensitive(False)
        else:
            tv = self.treeviewChannelChooser
            self.btnDownloadOpml.set_sensitive(True)
            self.entryURL.set_sensitive(True)

        tv.set_model(model)
        tv.set_sensitive(True)

    def thread_func(self, tab=0):
        if tab == 1:
            model = OpmlListModel(opml.Importer(self._config.toplist_url))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))
        elif tab == 2:
            model = OpmlListModel(youtube.find_youtube_channels(self.entryYoutubeSearch.get_text()))
            if len(model) == 0:
                self.notification(_('There are no YouTube channels that would match this query.'), _('No channels found'))
        else:
            url = self.entryURL.get_text()
            model = OpmlListModel(opml.Importer(url))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))

        util.idle_add(self.thread_finished, model, tab)
    
    def download_opml_file(self, url):
        self.entryURL.set_text(url)
        self.btnDownloadOpml.set_sensitive(False)
        self.entryURL.set_sensitive(False)
        self.btnOK.set_sensitive(False)
        self.treeviewChannelChooser.set_sensitive(False)
        threading.Thread(target=self.thread_func).start()
        threading.Thread(target=lambda: self.thread_func(1)).start()

    def select_all( self, value ):
        enabled = False
        model = self.get_treeview().get_model()
        if model is not None:
            for row in model:
                row[OpmlListModel.C_SELECTED] = value
                if value:
                    enabled = True
        self.btnOK.set_sensitive(enabled)

    def on_gPodderPodcastDirectory_destroy(self, widget, *args):
        pass

    def on_btnDownloadOpml_clicked(self, widget, *args):
        self.download_opml_file(self.entryURL.get_text())

    def on_btnSearchYouTube_clicked(self, widget, *args):
        self.entryYoutubeSearch.set_sensitive(False)
        self.treeviewYouTubeChooser.set_sensitive(False)
        self.btnSearchYouTube.set_sensitive(False)
        threading.Thread(target = lambda: self.thread_func(2)).start()

    def on_btnSelectAll_clicked(self, widget, *args):
        self.select_all(True)
    
    def on_btnSelectNone_clicked(self, widget, *args):
        self.select_all(False)

    def on_btnOK_clicked(self, widget, *args):
        channel_urls = self.get_selected_channels()
        self.gPodderPodcastDirectory.destroy()

        # add channels that have been selected
        if self.add_urls_callback is not None:
            self.add_urls_callback(channel_urls)

    def on_btnCancel_clicked(self, widget, *args):
        self.gPodderPodcastDirectory.destroy()

    def on_entryYoutubeSearch_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Return:
            self.on_btnSearchYouTube_clicked(widget)

    def get_treeview(self, tab=None):
        if tab is None:
            tab = self.notebookChannelAdder.get_current_page()

        if tab == 0:
            return self.treeviewChannelChooser
        elif tab == 1:
            return self.treeviewTopPodcastsChooser
        else:
            return self.treeviewYouTubeChooser

