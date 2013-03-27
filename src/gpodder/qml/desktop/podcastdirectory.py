# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

import urllib
import os.path

from gpodder.qml.common import _

from gpodder import util
from gpodder import opml
from gpodder import youtube
from gpodder import my
from PySide.QtCore import QObject, Signal, Slot

from gpodder.qml.desktop.model import OpmlListModel
from gpodder.qml.desktop.basiccontroller import BasicController


class TabType():
    ChannelChooser, TopPodcasts, Youtube = range(3)


class PodcastDirectory(BasicController):
    changed = Signal()
    updateModel = Signal(int, QObject)

    def __init__(self, parent, addPodcastsFunction):
        BasicController.__init__(self, parent)

        self.add_podcast_list = addPodcastsFunction
        self._models = {
            TabType.ChannelChooser: None,
            TabType.TopPodcasts: None,
            TabType.Youtube: None
        }

    def registerProperties(self, context):
        pass

    @Slot(QObject)
    def viewCreated(self, view):
        self.updateModel.connect(view.updateModel)

    def new(self):
        if hasattr(self, 'custom_title'):
            self.gPodderPodcastDirectory.set_title(self.custom_title)

        if hasattr(self, 'hide_url_entry'):
            self.hboxOpmlUrlEntry.hide_all()
            new_parent = self.notebookChannelAdder.get_parent()
            new_parent.remove(self.notebookChannelAdder)
            self.vboxOpmlImport.reparent(new_parent)

        if not hasattr(self, 'add_podcast_list'):
            self.add_podcast_list = None

        self.setup_treeview(self.treeviewChannelChooser)
        self.setup_treeview(self.treeviewTopPodcastsChooser)
        self.setup_treeview(self.treeviewYouTubeChooser)

        self.notebookChannelAdder.connect(
            'switch-page', lambda a, b, c: self.on_change_tab(c)
        )

    @Slot(unicode, result=str)
    def on_entryURL_changed(self, url):
        if self.is_search_term(url):
            return _('Search')
        else:
            return _('Download')

#    def setup_treeview(self, tv):
#        togglecell = gtk.CellRendererToggle()
#        togglecell.set_property( 'activatable', True)
#        togglecell.connect( 'toggled', self.callback_edited)
#        togglecolumn = gtk.TreeViewColumn( '', togglecell, active=OpmlListModel.C_SELECTED)
#        togglecolumn.set_min_width(40)
#
#        titlecell = gtk.CellRendererText()
#        titlecolumn = gtk.TreeViewColumn(_('Podcast'), titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)

#        for itemcolumn in (togglecolumn, titlecolumn):
#            tv.append_column(itemcolumn)

    def callback_edited(self, cell, path):
        model = self.get_treeview().get_model()
        model[path][OpmlListModel.C_SELECTED] = not model[path][OpmlListModel.C_SELECTED]
        self.btnOK.set_sensitive(bool(len(self.get_selected_channels())))

    def is_search_term(self, url):
        return ('://' not in url and not os.path.exists(url))

    def thread_func(self, tab, param=None):
        if tab == TabType.ChannelChooser:
            url = param
            if url is None:
                url = self.getInitialOMPLUrl()

            if self.is_search_term(url):
                url = 'http://gpodder.net/search.opml?q=' + urllib.quote(url)

            model = OpmlListModel(opml.Importer(url))

            if model.rowCount() == 0:
                self.notification(
                    _('The specified URL does not provide any valid OPML podcast items.'),
                    _('No feeds found')
                )

        elif tab == TabType.TopPodcasts:
            model = OpmlListModel(opml.Importer(my.TOPLIST_OPML))

            if model.rowCount() == 0:
                self.notification(
                    _('The specified URL does not provide any valid OPML podcast items.'),
                    _('No feeds found')
                )

        elif tab == TabType.Youtube:
            model = OpmlListModel(youtube.find_youtube_channels(param))

            if model.rowCount() == 0:
                self.notification(
                    _('There are no YouTube channels that would match this query.'),
                    _('No channels found')
                )

        self.setModel(tab, model)

    @Slot(unicode)
    def download_opml_file(self, url):
#        self.entryURL.set_text(url)
#        self.btnDownloadOpml.set_sensitive(False)
#        self.entryURL.set_sensitive(False)
#        self.btnOK.set_sensitive(False)
#        self.treeviewChannelChooser.set_sensitive(False)
#        util.run_in_background(self.thread_func)
        util.run_in_background(
            lambda: self.thread_func(TabType.ChannelChooser, url)
        )

    def on_gPodderPodcastDirectory_destroy(self, widget, *args):
        pass

    @Slot(unicode)
    def on_searchYouTube(self, text):
#        self.entryYoutubeSearch.set_sensitive(False)
#        self.treeviewYouTubeChooser.set_sensitive(False)
#        self.btnSearchYouTube.set_sensitive(False)
        util.run_in_background(
            lambda: self.thread_func(TabType.Youtube, text)
        )

    @Slot(QObject)
    def on_btnOK_clicked(self, model):
        channels = model.getSelected()

        # add channels that have been selected
        if channels is not None:
            urls = [channel.url for channel in channels]
            self.add_podcast_list(urls)

        self.close()

    def on_btnCancel_clicked(self, widget, *args):
        self.gPodderPodcastDirectory.destroy()

#    def on_entryYoutubeSearch_key_press_event(self, widget, event):
#        if event.keyval == gtk.keysyms.Return:
#            self.on_btnSearchYouTube_clicked(widget)

    @Slot(result=str)
    def getInitialOMPLUrl(self):
        return my.EXAMPLES_OPML

    @Slot(int, result=QObject)
    def getModel(self, tab):
        if tab in self._models:
            if self._models[tab] == None:
                util.run_in_background(
                    lambda: self.thread_func(tab)
                )
                return None

            return self._models[tab]
        else:
            return None

    @Slot(int, QObject)
    def setModel(self, tab, model):
        if tab in self._models:
            self._models[tab] = model
            self.updateModel.emit(tab, model)
