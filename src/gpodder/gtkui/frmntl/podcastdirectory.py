# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
import hildon

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import opml
from gpodder import youtube

from gpodder.gtkui.opml import OpmlListModel

from gpodder.gtkui.interface.common import BuilderWidget

from gpodder.gtkui.frmntl.widgets import EditToolbarDeluxe

class gPodderPodcastDirectory(BuilderWidget):
    def new(self):
        if hasattr(self, 'custom_title'):
            self.main_window.set_title(self.custom_title)

        if not hasattr(self, 'add_urls_callback'):
            self.add_urls_callback = None

        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn('', titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)
        self.treeview.append_column(titlecolumn)

        selection = self.treeview.get_selection()
        selection.connect('changed', self.on_selection_changed)
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.unselect_all()
        self.app_menu = hildon.AppMenu()
        for action in (self.action_load_opml, \
                       self.action_load_toplist, \
                       self.action_load_search, \
                       self.action_load_youtube, \
                       self.action_select_all, \
                       self.action_select_none):
            button = gtk.Button()
            action.connect_proxy(button)
            self.app_menu.append(button)
        self.main_window.set_app_menu(self.app_menu)

        self.edit_toolbar = EditToolbarDeluxe(self.main_window.get_title(), \
                _('Subscribe'))
        self.edit_toolbar.connect('arrow-clicked', \
                self.on_close_button_clicked)
        self.edit_toolbar.connect('button-clicked', \
                self.on_subscribe_button_clicked)
        self.edit_toolbar.show_all()

        # This method needs a EditToolbarDeluxe to work
        self.edit_toolbar.set_button_sensitive(False)

        self.main_window.set_edit_toolbar(self.edit_toolbar)
        self.main_window.fullscreen()
        self.main_window.show()

        self.app_menu.popup(self.main_window)

    def on_selection_changed(self, selection):
        self.set_subscribe_button_sensitive()

    def get_selected_channels(self):
        selection = self.treeview.get_selection()
        model, paths = selection.get_selected_rows()
        return [model.get_value(model.get_iter(path), \
                OpmlListModel.C_URL) for path in paths]

    def on_load_opml_button_clicked(self, widget):
        url = self.show_text_edit_dialog(_('Load OPML file from the web'), _('URL:'))
        if url is not None:
            self.download_opml_file(url)
    
    def on_load_toplist_button_clicked(self, widget):
        self.download_opml_file(self._config.toplist_url)
    
    def on_load_search_button_clicked(self, widget):
        search_term = self.show_text_edit_dialog(_('Search podcast.de'), \
                _('Search for:'))
        if search_term is not None:
            url = 'http://api.podcast.de/opml/podcasts/suche/%s' % \
                    (urllib.quote(search_term),)
            self.download_opml_file(url)

    def on_load_youtube_button_clicked(self, widget):
        search_term = self.show_text_edit_dialog(\
                _('Search YouTube user channels'), \
                _('Search for:'))
        if search_term is not None:
            self.download_opml_file(search_term, use_youtube=True)
    
    def download_opml_file(self, url, use_youtube=False):
        selection = self.treeview.get_selection()
        selection.unselect_all()
        self.treeview.set_sensitive(False)

        banner = hildon.hildon_banner_show_animation(self.main_window, \
                '', _('Loading podcast list, please wait'))
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, True)

        def download_thread_func():
            if use_youtube:
                importer = youtube.find_youtube_channels(url)
            else:
                importer = opml.Importer(url)

            if importer.items:
                model = OpmlListModel(importer)
            else:
                model = None
            def download_thread_finished():
                if banner is not None:
                    banner.destroy()
                hildon.hildon_gtk_window_set_progress_indicator(\
                        self.main_window, False)
                self.action_select_all.set_property('visible', \
                        model is not None)
                self.action_select_none.set_property('visible', \
                        model is not None)
                self.treeview.set_model(model)
                self.treeview.set_sensitive(True)
                self.set_subscribe_button_sensitive()

                if model is None:
                    self.show_message(_('No podcasts found. Try another source.'), \
                            important=True)
                    self.app_menu.popup(self.main_window)

            util.idle_add(download_thread_finished)

        threading.Thread(target=download_thread_func).start()

    def on_select_all_button_clicked(self, widget):
        selection = self.treeview.get_selection()
        selection.select_all()

    def on_select_none_button_clicked(self, widget):
        selection = self.treeview.get_selection()
        selection.unselect_all()

    def set_subscribe_button_sensitive(self):
        selection = self.treeview.get_selection()
        count = selection.count_selected_rows()
        title = self.main_window.get_title()
        if count == 1:
            title += ' - %s' % (_('1 podcast selected'),)
        elif count > 1:
            title += ' - %s' % (_('%d podcasts selected') % count,)
        self.edit_toolbar.set_label(title)
        self.edit_toolbar.set_button_sensitive(count > 0)

    def on_subscribe_button_clicked(self, widget, *args):
        channel_urls = self.get_selected_channels()
        self.main_window.destroy()

        # add channels that have been selected
        if self.add_urls_callback is not None:
            self.add_urls_callback(channel_urls)

    def on_close_button_clicked(self, widget):
        self.main_window.destroy()

