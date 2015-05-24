# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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
# gpodder.gtkui.desktop.podcastdirectory - Podcast directory Gtk UI
# Thomas Perl <thp@gpodder.org>; 2014-10-22
#


import gtk
import pango
import cgi
import os

import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import directory

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.progress import ProgressIndicator
from gpodder.gtkui.interface.tagcloud import TagCloud

class DirectoryPodcastsModel(gtk.ListStore):
    C_SELECTED, C_MARKUP, C_TITLE, C_URL = range(4)

    def __init__(self, callback_can_subscribe):
        gtk.ListStore.__init__(self, bool, str, str, str)
        self.callback_can_subscribe = callback_can_subscribe

    def load(self, directory_entries):
        self.clear()
        for entry in directory_entries:
            if entry.subscribers != -1:
                self.append((False, '%s (%d)\n<small>%s</small>' % (cgi.escape(entry.title),
                    entry.subscribers, cgi.escape(entry.url)), entry.title, entry.url))
            else:
                self.append((False, '%s\n<small>%s</small>' % (cgi.escape(entry.title),
                    cgi.escape(entry.url)), entry.title, entry.url))
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def toggle(self, path):
        self[path][self.C_SELECTED] = not self[path][self.C_SELECTED]
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def set_selection_to(self, selected):
        for row in self:
            row[self.C_SELECTED] = selected
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def get_selected_podcasts(self):
        return [(row[self.C_TITLE], row[self.C_URL]) for row in self if row[self.C_SELECTED]]


class DirectoryProvidersModel(gtk.ListStore):
    C_WEIGHT, C_TEXT, C_ICON, C_PROVIDER = range(4)

    SEPARATOR = (pango.WEIGHT_NORMAL, '', None, None)

    def __init__(self, providers):
        gtk.ListStore.__init__(self, int, str, gtk.gdk.Pixbuf, object)
        for provider in providers:
            self.add_provider(provider() if provider else None)

    def add_provider(self, provider):
        if provider is None:
            self.append(self.SEPARATOR)
        else:
            try:
                pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(gpodder.images_folder, provider.icon)) if provider.icon else None
            except Exception as e:
                logger.warn('Could not load icon: %s (%s)', provider.icon or '-', e)
                pixbuf = None
            self.append((pango.WEIGHT_NORMAL, provider.name, pixbuf, provider))

    def is_row_separator(self, model, it):
        return self.get_value(it, self.C_PROVIDER) is None


class gPodderPodcastDirectory(BuilderWidget):
    def new(self):
        if hasattr(self, 'custom_title'):
            self.main_window.set_title(self.custom_title)

        if not hasattr(self, 'add_podcast_list'):
            self.add_podcast_list = None

        self.providers_model = DirectoryProvidersModel(directory.PROVIDERS)
        self.podcasts_model = DirectoryPodcastsModel(self.on_can_subscribe_changed)
        self.current_provider = None
        self.podcasts_progress_indicator = None

        self.setup_providers_treeview()
        self.setup_podcasts_treeview()
        self.setup_tag_cloud()

        selection = self.tv_providers.get_selection()
        selection.select_path((0,))
        self.on_tv_providers_row_activated(self.tv_providers, (0,), None)

        self.main_window.show()

    def download_opml_file(self, filename):
        self.providers_model.add_provider(directory.FixedOpmlFileProvider(filename))
        self.tv_providers.set_cursor(len(self.providers_model)-1)

    def setup_podcasts_treeview(self):
        column = gtk.TreeViewColumn('')
        cell = gtk.CellRendererToggle()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'active', DirectoryPodcastsModel.C_SELECTED)
        cell.connect('toggled', lambda cell, path: self.podcasts_model.toggle(path))
        self.tv_podcasts.append_column(column)

        column = gtk.TreeViewColumn('')
        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell)
        column.add_attribute(cell, 'markup', DirectoryPodcastsModel.C_MARKUP)
        self.tv_podcasts.append_column(column)

        self.tv_podcasts.set_model(self.podcasts_model)
        self.podcasts_model.append((False, 'a', 'b', 'c'))

    def setup_providers_treeview(self):
        column = gtk.TreeViewColumn('')
        cell = gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', DirectoryProvidersModel.C_ICON)
        cell = gtk.CellRendererText()
        #cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell)
        column.add_attribute(cell, 'text', DirectoryProvidersModel.C_TEXT)
        column.add_attribute(cell, 'weight', DirectoryProvidersModel.C_WEIGHT)
        self.tv_providers.append_column(column)

        self.tv_providers.set_row_separator_func(self.providers_model.is_row_separator)

        self.tv_providers.set_model(self.providers_model)

    def setup_tag_cloud(self):
        self.tag_cloud = TagCloud()
        self.tag_cloud.set_size_request(-1, 130)
        self.tag_cloud.show_all()
        self.sw_tagcloud.add(self.tag_cloud)

        self.tag_cloud.connect('selected', self.on_tag_selected)

    def on_tag_selected(self, tag_cloud, tag):
        self.obtain_podcasts_with(lambda: self.current_provider.on_tag(tag))

    def on_tv_providers_row_activated(self, treeview, path, column):
        it = self.providers_model.get_iter(path)

        for row in self.providers_model:
            row[DirectoryProvidersModel.C_WEIGHT] = pango.WEIGHT_NORMAL

        if it:
            self.providers_model.set_value(it, DirectoryProvidersModel.C_WEIGHT, pango.WEIGHT_BOLD)
            provider = self.providers_model.get_value(it, DirectoryProvidersModel.C_PROVIDER)
            self.use_provider(provider)

    def use_provider(self, provider):
        self.podcasts_model.clear()
        self.current_provider = provider

        if provider.kind == directory.Provider.PROVIDER_SEARCH:
            self.lb_search.set_text('Search:')
            self.bt_search.set_label('Search')
        elif provider.kind == directory.Provider.PROVIDER_URL:
            self.lb_search.set_text('URL:')
            self.bt_search.set_label('Download')
        elif provider.kind == directory.Provider.PROVIDER_FILE:
            self.lb_search.set_text('Filename:')
            self.bt_search.set_label('Open')
        elif provider.kind == directory.Provider.PROVIDER_TAGCLOUD:
            self.tag_cloud.clear_tags()

            @util.run_in_background
            def load_tags():
                try:
                    tags = [(t.tag, t.weight) for t in provider.get_tags()]
                except Exception as e:
                    logger.warn('Got exception while loading tags: %s', e)
                    tags = []

                @util.idle_add
                def update_ui():
                    self.tag_cloud.set_tags(tags)
        elif provider.kind == directory.Provider.PROVIDER_STATIC:
            self.obtain_podcasts_with(provider.on_static)

        if provider.kind in (directory.Provider.PROVIDER_SEARCH,
                directory.Provider.PROVIDER_URL,
                directory.Provider.PROVIDER_FILE):
            self.en_query.set_text('')
            self.hb_text_entry.show()
            util.idle_add(self.en_query.grab_focus)
        else:
            self.hb_text_entry.hide()

        if provider.kind == directory.Provider.PROVIDER_TAGCLOUD:
            self.sw_tagcloud.show()
        else:
            self.sw_tagcloud.hide()


    def on_tv_providers_cursor_changed(self, treeview):
        path, column = treeview.get_cursor()
        self.on_tv_providers_row_activated(treeview, path, column)

    def obtain_podcasts_with(self, callback):
        if self.podcasts_progress_indicator is not None:
            self.podcasts_progress_indicator.on_finished()

        self.podcasts_progress_indicator = ProgressIndicator(_('Loading podcasts'),
                _('Please wait while the podcast list is downloaded'),
                parent=self.main_window)

        original_provider = self.current_provider

        self.en_query.set_sensitive(False)
        self.bt_search.set_sensitive(False)
        self.tag_cloud.set_sensitive(False)
        self.podcasts_model.clear()

        @util.run_in_background
        def download_data():
            try:
                podcasts = callback()
            except Exception as e:
                logger.warn('Got exception while loading podcasts: %s', e)
                podcasts = []

            @util.idle_add
            def update_ui():
                if self.podcasts_progress_indicator is not None:
                    self.podcasts_progress_indicator.on_finished()
                    self.podcasts_progress_indicator = None

                if original_provider != self.current_provider:
                    logger.warn('Ignoring update from old thread')
                    return

                self.podcasts_model.load(podcasts or [])
                self.en_query.set_sensitive(True)
                self.bt_search.set_sensitive(True)
                self.tag_cloud.set_sensitive(True)
                self.en_query.grab_focus()

    def on_bt_search_clicked(self, widget):
        if self.current_provider is None:
            return

        query = self.en_query.get_text()

        @self.obtain_podcasts_with
        def load_data():
            if self.current_provider.kind == directory.Provider.PROVIDER_SEARCH:
                return self.current_provider.on_search(query)
            elif self.current_provider.kind == directory.Provider.PROVIDER_URL:
                return self.current_provider.on_url(query)
            elif self.current_provider.kind == directory.Provider.PROVIDER_FILE:
                return self.current_provider.on_file(query)

    def on_can_subscribe_changed(self, can_subscribe):
        self.btnOK.set_sensitive(can_subscribe)

    def on_btnSelectAll_clicked(self, widget, *args):
        self.podcasts_model.set_selection_to(True)

    def on_btnSelectNone_clicked(self, widget, *args):
        self.podcasts_model.set_selection_to(False)

    def on_btnOK_clicked(self, widget, *args):
        urls = self.podcasts_model.get_selected_podcasts()

        self.main_window.destroy()

        # add channels that have been selected
        if self.add_podcast_list is not None:
            self.add_podcast_list(urls)

    def on_btnCancel_clicked(self, widget, *args):
        self.main_window.destroy()
