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


class gPodderPodcastDirectory(BuilderWidget):
    finger_friendly_widgets = ('button_cancel', 'button_subscribe')
    
    def new(self):
        if hasattr(self, 'custom_title'):
            self.main_window.set_title(self.custom_title)

        if not hasattr(self, 'add_urls_callback'):
            self.add_urls_callback = None

        if gpodder.ui.diablo:
            togglecell = gtk.CellRendererToggle()
            togglecolumn = gtk.TreeViewColumn('', togglecell, active=OpmlListModel.C_SELECTED)
            self.treeview.append_column(togglecolumn)
        
        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn('', titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)
        self.treeview.append_column(titlecolumn)

        self.treeview.connect('button-release-event', \
                self.on_treeview_button_release)

        if gpodder.ui.diablo:
            menu = gtk.Menu()
            item = gtk.MenuItem(_('Load podcast list'))
            submenu = gtk.Menu()
            submenu.append(self.action_load_opml.create_menu_item())
            submenu.append(self.action_load_toplist.create_menu_item())
            submenu.append(self.action_load_search.create_menu_item())
            submenu.append(self.action_load_youtube.create_menu_item())
            item.set_submenu(submenu)
            menu.append(item)
            menu.append(gtk.SeparatorMenuItem())
            menu.append(self.action_select_all.create_menu_item())
            menu.append(self.action_select_none.create_menu_item())
            menu.append(gtk.SeparatorMenuItem())
            menu.append(self.action_invert_selection.create_menu_item())
            menu.append(gtk.SeparatorMenuItem())
            menu.append(self.action_close.create_menu_item())
            self.main_window.set_menu(self.set_finger_friendly(menu))
        elif gpodder.ui.fremantle:
            selection = self.treeview.get_selection()
            selection.connect('changed', self.on_selection_changed)
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            selection.unselect_all()
            appmenu = hildon.AppMenu()
            for action in (self.action_load_opml, \
                           self.action_load_toplist, \
                           self.action_load_search, \
                           self.action_load_youtube, \
                           self.action_select_all, \
                           self.action_select_none):
                button = gtk.Button()
                action.connect_proxy(button)
                appmenu.append(button)
            self.main_window.set_app_menu(appmenu)

    def on_selection_changed(self, selection):
        self.set_subscribe_button_sensitive()

    def on_treeview_button_release(self, widget, event):
        if gpodder.ui.diablo:
            selection = widget.get_selection()
            model, iter = selection.get_selected()
            if iter is not None:
                model.set_value(iter, OpmlListModel.C_SELECTED, \
                        not model.get_value(iter, OpmlListModel.C_SELECTED))
            self.set_subscribe_button_sensitive()

    def get_selected_channels(self):
        if gpodder.ui.diablo:
            model = self.treeview.get_model()
            if model is not None:
                return [row[OpmlListModel.C_URL] for row in model \
                        if row[OpmlListModel.C_SELECTED]]
        elif gpodder.ui.fremantle:
            selection = self.treeview.get_selection()
            model, paths = selection.get_selected_rows()
            return [model.get_value(model.get_iter(path), \
                    OpmlListModel.C_URL) for path in paths]

        return []

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
        self.treeview.get_selection().unselect_all()
        self.treeview.set_sensitive(False)
        self.button_subscribe.set_sensitive(False)

        if gpodder.ui.diablo:
            self.button_cancel.set_sensitive(False)
            banner = hildon.hildon_banner_show_animation(self.main_window, \
                    None, _('Loading podcast list, please wait'))
        elif gpodder.ui.fremantle:
            banner = hildon.hildon_banner_show_animation(self.main_window, \
                    '', _('Loading podcast list, please wait'))
        else:
            banner = None

        def download_thread_func():
            if use_youtube:
                importer = youtube.find_youtube_channels(url)
            else:
                importer = opml.Importer(url)

            if importer.items:
                model = OpmlListModel(importer)
            else:
                model = None
                self.show_message(_('Please pick another source.'), _('No podcasts found'))

            def download_thread_finished():
                if banner is not None:
                    banner.destroy()
                self.treeview.set_model(model)
                self.treeview.set_sensitive(True)
                if gpodder.ui.diablo:
                    self.button_cancel.set_sensitive(True)
                self.set_subscribe_button_sensitive()
            util.idle_add(download_thread_finished)

        threading.Thread(target=download_thread_func).start()

    def on_select_all_button_clicked(self, widget):
        self.do_select(all=True)

    def on_select_none_button_clicked(self, widget):
        self.do_select(all=False)

    def on_invert_selection_button_clicked(self, widget):
        self.do_select(invert=True)

    def do_select(self, all=False, invert=False):
        model = self.treeview.get_model()
        if model is not None:
            if gpodder.ui.diablo:
                for row in model:
                    if invert:
                        row[OpmlListModel.C_SELECTED] = \
                                not row[OpmlListModel.C_SELECTED]
                    else:
                        row[OpmlListModel.C_SELECTED] = all
            elif gpodder.ui.fremantle:
                if invert:
                    raise Exception('Not implemented for Fremantle')
                selection = self.treeview.get_selection()
                if all:
                    selection.select_all()
                else:
                    selection.unselect_all()
        self.set_subscribe_button_sensitive()

    def set_subscribe_button_sensitive(self):
        if gpodder.ui.diablo:
            model = self.treeview.get_model()
            if model is not None:
                for row in model:
                    if row[OpmlListModel.C_SELECTED]:
                        self.button_subscribe.set_sensitive(True)
                        return
            self.button_subscribe.set_sensitive(False)
        elif gpodder.ui.fremantle:
            selection = self.treeview.get_selection()
            count = selection.count_selected_rows()
            self.button_subscribe.set_sensitive(count > 0)

    def on_subscribe_button_clicked(self, widget, *args):
        channel_urls = self.get_selected_channels()
        self.main_window.destroy()

        # add channels that have been selected
        if self.add_urls_callback is not None:
            self.add_urls_callback(channel_urls)

    def on_close_button_clicked(self, widget):
        self.main_window.destroy()

