# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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


import html
import logging
import os
import traceback

from gi.repository import Gdk, GdkPixbuf, Gtk, Pango

import gpodder
from gpodder import directory, util
from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.progress import ProgressIndicator
from gpodder.gtkui.interface.tagcloud import TagCloud

_ = gpodder.gettext

logger = logging.getLogger(__name__)


class DirectoryPodcastsModel(Gtk.ListStore):
    C_SELECTED, C_MARKUP, C_TITLE, C_URL, C_SECTION = list(range(5))

    def __init__(self, callback_can_subscribe):
        Gtk.ListStore.__init__(self, bool, str, str, str, str)
        self.callback_can_subscribe = callback_can_subscribe

    def load(self, directory_entries):
        self.clear()
        for entry in directory_entries:
            if entry.subscribers != -1:
                subscribers_part = '(%d)' % entry.subscribers
            else:
                subscribers_part = ''
            if entry.section:
                section_part = '%s\n' % (html.escape(entry.section))
            else:
                section_part = ''
            self.append((False, '%s%s%s\n<small>%s</small>' % (section_part, html.escape(entry.title),
                subscribers_part, html.escape(entry.url)), entry.title, entry.url, entry.section))
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def toggle(self, path):
        self[path][self.C_SELECTED] = not self[path][self.C_SELECTED]
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def set_selection_to(self, selected):
        for row in self:
            row[self.C_SELECTED] = selected
        self.callback_can_subscribe(len(self.get_selected_podcasts()) > 0)

    def get_selected_podcasts(self):
        return [(row[self.C_TITLE], row[self.C_URL], row[self.C_SECTION]) for row in self if row[self.C_SELECTED]]


class DirectoryProvidersModel(Gtk.ListStore):
    C_WEIGHT, C_TEXT, C_ICON, C_PROVIDER = list(range(4))

    SEPARATOR = (Pango.Weight.NORMAL, '', None, None)

    def __init__(self, providers):
        Gtk.ListStore.__init__(self, int, str, GdkPixbuf.Pixbuf, object)
        for provider in providers:
            instance = provider() if provider else None
            if instance is not None and instance.kind == directory.Provider.PROVIDER_TAGCLOUD:
                logger.warning("PROVIDER_TAGCLOUD is unsupported")
            else:
                self.add_provider(instance)

    def add_provider(self, provider):
        if provider is None:
            self.append(self.SEPARATOR)
        else:
            pixbuf = None
            if provider.icon:
                search_path = {gpodder.images_folder, }
                # let an extension provide an icon by putting it next to the source code
                for e in gpodder.user_extensions.filenames:
                    search_path.add(os.path.dirname(e))
                for d in search_path:
                    path_to_try = os.path.join(d, provider.icon)
                    if os.path.exists(path_to_try):
                        try:
                            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path_to_try)
                            break
                        except Exception as e:
                            logger.warning('Could not load icon: %s (%s)', provider.icon, e)
            self.append((Pango.Weight.NORMAL, provider.name, pixbuf, provider))

    def is_row_separator(self, model, it):
        return self.get_value(it, self.C_PROVIDER) is None


class gPodderPodcastDirectory(BuilderWidget):
    def new(self):
        self.gPodderPodcastDirectory.set_transient_for(self.parent_widget)
        if hasattr(self, 'custom_title'):
            self.main_window.set_title(self.custom_title)

        if not hasattr(self, 'add_podcast_list'):
            self.add_podcast_list = None

        self.providers_model = DirectoryProvidersModel(directory.PROVIDERS)
        self.podcasts_model = DirectoryPodcastsModel(self.on_can_subscribe_changed)
        self.current_provider = None

        self.setup_providers_treeview()
        self.setup_podcasts_treeview()

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.KEY_Escape, 0, Gtk.AccelFlags.VISIBLE, self.on_escape)
        self.main_window.add_accel_group(accel)

        self._config.connect_gtk_window(self.main_window, 'podcastdirectory', True)

        self.btnBack.hide()
        self.main_window.show()

    def download_opml_file(self, filename):
        provider = directory.FixedOpmlFileProvider(filename)
        self.providers_model.add_provider(provider)
        self.tv_providers.set_cursor(len(self.providers_model) - 1)
        self.use_provider(provider, allow_back=False)

    def setup_podcasts_treeview(self):
        column = Gtk.TreeViewColumn('')
        cell = Gtk.CellRendererToggle()
        cell.set_fixed_size(48, -1)
        column.pack_start(cell, False)
        column.add_attribute(cell, 'active', DirectoryPodcastsModel.C_SELECTED)
        cell.connect('toggled', lambda cell, path: self.podcasts_model.toggle(path))
        self.tv_podcasts.append_column(column)

        column = Gtk.TreeViewColumn('')
        cell = Gtk.CellRendererText()
        cell.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'markup', DirectoryPodcastsModel.C_MARKUP)
        self.tv_podcasts.append_column(column)

        self.tv_podcasts.set_model(self.podcasts_model)
        self.podcasts_model.append((False, 'a', 'b', 'c', 'd'))

    def setup_providers_treeview(self):
        column = Gtk.TreeViewColumn('')
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', DirectoryProvidersModel.C_ICON)
        cell = Gtk.CellRendererText()
        # cell.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', DirectoryProvidersModel.C_TEXT)
        column.add_attribute(cell, 'weight', DirectoryProvidersModel.C_WEIGHT)
        self.tv_providers.append_column(column)

        self.tv_providers.set_row_separator_func(self.providers_model.is_row_separator)

        self.tv_providers.set_model(self.providers_model)

        self.tv_providers.connect("row-activated", self.on_tv_providers_row_activated)

    def on_tv_providers_row_activated(self, treeview, path, column):
        it = self.providers_model.get_iter(path)

        for row in self.providers_model:
            row[DirectoryProvidersModel.C_WEIGHT] = Pango.Weight.NORMAL

        if it:
            self.providers_model.set_value(it, DirectoryProvidersModel.C_WEIGHT, Pango.Weight.BOLD)
            provider = self.providers_model.get_value(it, DirectoryProvidersModel.C_PROVIDER)
            self.use_provider(provider)

    def use_provider(self, provider, allow_back=True):
        self.podcasts_model.clear()
        self.current_provider = provider
        self.main_window.set_title(provider.name)

        if provider.kind == directory.Provider.PROVIDER_SEARCH:
            self.lb_search.set_text(_('Search:'))
            self.bt_search.set_label(_('Search'))
        elif provider.kind == directory.Provider.PROVIDER_URL:
            self.lb_search.set_text(_('URL:'))
            self.bt_search.set_label(_('Download'))
        elif provider.kind == directory.Provider.PROVIDER_FILE:
            self.lb_search.set_text(_('Filename:'))
            self.bt_search.set_label(_('Open'))
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
        self.progressBar.set_fraction(0)
        self.progressLabel.set_label('')
        self.txtError.hide()
        self.stState.set_visible_child(self.stPodcasts)
        self.btnBack.set_visible(allow_back)

    def obtain_podcasts_with(self, callback):
        self.progressBar.set_fraction(0.1)
        self.progressLabel.set_text(_('Please wait while the podcast list is downloaded'))
        self.txtError.hide()
        self.stackProgressErrorPodcasts.set_visible_child(self.stProgError)
        self.selectbox.hide()
        self.btnOK.hide()

        original_provider = self.current_provider

        self.en_query.set_sensitive(False)
        self.bt_search.set_sensitive(False)
        self.podcasts_model.clear()

        @util.run_in_background
        def download_data():
            podcasts = []
            error = None
            try:
                podcasts = callback()
            except directory.JustAWarning as e:
                error = e
            except Exception as e:
                logger.warning(
                    'Got exception while loading podcasts: %r', e,
                    exc_info=True)
                error = e

            @util.idle_add
            def update_ui():
                self.progressBar.set_fraction(1)

                if original_provider == self.current_provider:
                    self.podcasts_model.load(podcasts or [])
                    if error:
                        self.progressLabel.set_text(_("Error"))
                        if isinstance(error, directory.JustAWarning):
                            self.txtError.get_buffer().set_text(error.warning)
                        else:
                            self.txtError.get_buffer().set_text(_("Error: %s\n\n%s") % (error, "".join(traceback.format_exception(error))))
                        self.txtError.show()
                    elif not podcasts:
                        self.progressLabel.set_text(_("No results"))
                        self.txtError.get_buffer().set_text(_("Sorry, no podcasts were found"))
                        self.txtError.show()
                    else:
                        self.stackProgressErrorPodcasts.set_visible_child(self.sw_podcasts)
                        self.selectbox.show()
                        self.btnOK.show()
                else:
                    logger.warning('Ignoring update from old thread')

                self.en_query.set_sensitive(True)
                self.bt_search.set_sensitive(True)
                if self.en_query.get_realized():
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

    def on_btnBack_clicked(self, widget, *args):
        self.stState.set_visible_child(self.stProviders)
        widget.hide()
        self.selectbox.hide()
        self.btnOK.hide()

    def on_escape(self, *args, **kwargs):
        if self.stState.get_visible_child() == self.stProviders:
            self.main_window.destroy()
        else:
            self.on_btnBack_clicked(self.btnBack)
