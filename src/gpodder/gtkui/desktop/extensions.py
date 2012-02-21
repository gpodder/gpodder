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
import os.path
import cgi

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

import logging
logger = logging.getLogger(__name__)

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderExtensionManager(BuilderWidget):
    C_INDEX, C_TOGGLE, C_LABEL, C_EXTENSIONCONTAINER = range(4)

    def new(self):
        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect('toggled', self.toggle_cell_handler)
        toggle_column = gtk.TreeViewColumn('', toggle_cell, active=self.C_TOGGLE)
        toggle_column.set_clickable(True)
        self.treeviewExtensions.append_column(toggle_column)

        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(_('Name'), renderer, markup=self.C_LABEL)
        column.set_clickable(False)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeviewExtensions.append_column(column)

        self.model = gtk.ListStore(int, bool, str, object)

        for index, (container, enabled) in enumerate(
                gpodder.user_extensions.get_extensions()):
            label = '%s\n<small>%s</small>' % (
                    cgi.escape(container.metadata.title),
                    cgi.escape(container.metadata.description))

            self.model.append([index, enabled, label, container])

        self.model.set_sort_column_id(self.C_LABEL, gtk.SORT_ASCENDING)
        self.treeviewExtensions.set_model(self.model)
        self.treeviewExtensions.columns_autosize()

    def _set_enabled_extension_in_config(self, model, path):
        it = model.get_iter(path)
        container = model.get_value(it, self.C_EXTENSIONCONTAINER)

        is_enabled = (container.name in self._config.extensions.enabled)
        new_enabled = not model.get_value(it, self.C_TOGGLE)

        if new_enabled and not is_enabled:
            try:
                container.load_extension()
            except Exception, e:
                logger.error('Cannot load extension: %s', e, exc_info=True)
                return

            self._config.extensions.enabled.append(container.name)
        elif not new_enabled and is_enabled:
            self._config.extensions.enabled.remove(container.name)

        self._config.schedule_save()
        model.set_value(it, self.C_TOGGLE, new_enabled)

    def _get_selected_extension_container(self):
        selection = self.treeviewExtensions.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return None

        return model.get_value(iter, self.C_EXTENSIONCONTAINER)

    def on_button_close_clicked(self, widget):
        # sync enabled/disabled extensions
        gpodder.user_extensions.get_extensions()

        # close extension preference window
        self.main_window.destroy()

    def on_btnOK_clicked(self, widget):
        self.on_button_close_clicked(widget)

    def toggle_cell_handler(self, cell, path):
        model = self.treeviewExtensions.get_model()
        self._set_enabled_extension_in_config(model, path)

    def on_row_activated(self, treeview, path, view_column):
        model = treeview.get_model()
        self._set_enabled_extension_in_config(model, path)

    def on_selection_changed(self, treeselection):
        model, iter = treeselection.get_selected()
        if not iter:
            value = False
        else:
            value = model.get_value(iter, self.C_TOGGLE)

    def treeview_show_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # TODO: Copied some of the code from src/gpodder/gtkui/desktop/episodeselector.py (gPodderEpisodeSelector.treeview_episodes_query_tooltip)
        #       maybe we should don't duplicate the code and implement this as a function globaly?!

        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos(x, y) or (None,)*4

        if column != treeview.get_columns()[1]:
            return False

        model = treeview.get_model()
        iter = model.get_iter(path)
        description = model.get_value(iter, self.C_TOOLTIP)
        if description:
            tooltip.set_text(description)
            return True
        else:
            return False
