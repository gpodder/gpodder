# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

import gtk
import pango
import threading
import hildon
import urllib
import gobject

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util
from gpodder import opml
from gpodder import youtube

from gpodder.gtkui.frmntl.opml import OpmlListModel

from gpodder.gtkui.interface.common import BuilderWidget

from gpodder.gtkui.frmntl.widgets import EditToolbarDeluxe

from gpodder.gtkui.draw import draw_text_box_centered

class gPodderPodcastDirectory(BuilderWidget):
    def new(self):
        self._is_updating = False

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
        for action in (self.action_select_all, \
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

    @classmethod
    def show_add_podcast_picker(cls, parent, toplist_url, opml_url, \
            add_urls_callback, subscribe_to_url_callback, \
            my_gpodder_callback, show_text_edit_dialog):
        dialog = gtk.Dialog(_('Select a source'), parent)
        pannable_area = hildon.PannableArea()
        pannable_area.set_size_request_policy(hildon.SIZE_REQUEST_CHILDREN)
        dialog.vbox.pack_start(pannable_area, expand=True)
        vbox = gtk.VBox(spacing=1)
        pannable_area.add_with_viewport(vbox)

        def load_opml_from_url(url):
            if url is not None:
                o = cls(parent, add_urls_callback=add_urls_callback)
                o.download_opml_file(url)

        def choice_enter_feed_url(widget):
            dialog.destroy()
            subscribe_to_url_callback()

        def choice_load_opml_from_url(widget):
            dialog.destroy()
            url = show_text_edit_dialog(_('Load OPML file from the web'), \
                    _('URL:'), is_url=True, affirmative_text=_('Load'))
            load_opml_from_url(url)

        def choice_search_mygpo(widget):
            dialog.destroy()
            search_term = show_text_edit_dialog(\
                    _('Search on gpodder.net'), \
                    _('Search for:'), affirmative_text=_('Search'))
            if search_term is not None:
                url = 'http://gpodder.net/search.opml?q=%s' % (urllib.quote(search_term),)
                load_opml_from_url(url)

        def choice_load_opml_from_file(widget):
            dialog.destroy()
            dlg = gobject.new(hildon.FileChooserDialog, \
                    action=gtk.FILE_CHOOSER_ACTION_OPEN)
            dlg.set_title(_('Open OPML file'))
            dlg.show_all()
            dlg.run()
            filename = dlg.get_filename()
            dlg.hide()
            if filename is not None:
                load_opml_from_url(filename)

        def choice_load_examples(widget):
            dialog.destroy()
            load_opml_from_url(opml_url)

        def choice_load_toplist(widget):
            dialog.destroy()
            load_opml_from_url(toplist_url)

        def choice_search_youtube(widget):
            dialog.destroy()
            search_term = show_text_edit_dialog(\
                    _('Search YouTube user channels'), \
                    _('Search for:'), affirmative_text=_('Search'))
            if search_term is not None:
                url = 'youtube://%s' % (search_term,)
                load_opml_from_url(url)

        def choice_mygpodder(widget):
            dialog.destroy()
            my_gpodder_callback()

        choices = (
                (_('Podcast feed/website URL'), choice_enter_feed_url),
                (_('OPML file from the web'), choice_load_opml_from_url),
                (_('Search on gpodder.net'), choice_search_mygpo),
                (_('Open OPML file'), choice_load_opml_from_file),
                (_('Example podcasts'), choice_load_examples),
                (_('Podcast Top 50'), choice_load_toplist),
                (_('Search YouTube users'), choice_search_youtube),
                (_('Download from gpodder.net'), choice_mygpodder),
        )

        for caption, handler in choices:
            button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | \
                    gtk.HILDON_SIZE_FINGER_HEIGHT, \
                    hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_text(caption, '')
            button.connect('clicked', handler)
            vbox.pack_start(button)

        dialog.show_all()

    def on_treeview_expose_event(self, treeview, event):
        if event.window == treeview.get_bin_window():
            model = treeview.get_model()
            if (model is not None and model.get_iter_first() is not None):
                return False

            ctx = event.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                    event.area.width, event.area.height)
            ctx.clip()
            x, y, width, height, depth = event.window.get_geometry()

            if self._is_updating:
                text = _('Loading podcast list')
            else:
                text = _('No podcasts')

            from gpodder.gtkui.frmntl import style
            font_desc = style.get_font_desc('LargeSystemFont')
            draw_text_box_centered(ctx, treeview, width, height, text, font_desc)

        return False


    def on_selection_changed(self, selection):
        self.set_subscribe_button_sensitive()

    def get_selected_channels(self):
        selection = self.treeview.get_selection()
        model, paths = selection.get_selected_rows()
        return [model.get_value(model.get_iter(path), \
                OpmlListModel.C_URL) for path in paths]

    def download_opml_file(self, url):
        selection = self.treeview.get_selection()
        selection.unselect_all()
        self.treeview.set_model(None)
        self._is_updating = True
        self.treeview.queue_draw()
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, True)

        def download_thread_func():
            if url.startswith('youtube://'):
                importer = youtube.find_youtube_channels(\
                        url[len('youtube://'):])
            else:
                importer = opml.Importer(url)

            if importer.items:
                model = OpmlListModel(importer)
            else:
                model = None
            def download_thread_finished():
                self._is_updating = False
                self.treeview.queue_draw()
                hildon.hildon_gtk_window_set_progress_indicator(\
                        self.main_window, False)
                self.action_select_all.set_property('visible', \
                        model is not None)
                self.action_select_none.set_property('visible', \
                        model is not None)
                self.treeview.set_model(model)
                self.set_subscribe_button_sensitive()

                if model is None:
                    self.show_message(_('No podcasts found. Try another source.'), \
                            important=True)
                    self.main_window.destroy()

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
        title = [self.main_window.get_title()]
        if selection:
            count = selection.count_selected_rows()
            text = N_('%(count)d podcast selected', '%(count)d podcasts selected', count)
            title.append(text % {'count': count})
        else:
            count = 0
        self.edit_toolbar.set_label(' - '.join(title))
        self.edit_toolbar.set_button_sensitive(count > 0)

    def on_subscribe_button_clicked(self, widget, *args):
        channel_urls = self.get_selected_channels()
        self.main_window.destroy()

        # add channels that have been selected
        if self.add_urls_callback is not None:
            self.add_urls_callback(channel_urls)

    def on_close_button_clicked(self, widget):
        self.main_window.destroy()

