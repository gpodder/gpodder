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

import gobject
import gtk
import pango
import os.path

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

import logging
logger = logging.getLogger(__name__)

from gpodder.gtkui.interface.common import BuilderWidget


class ExtensionTextItem(gtk.VBox):
    def __init__(self, key, settings, value):
        gtk.VBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.key = key

        self.__label = gtk.Label(settings['desc'])
        self.__label.set_alignment(0, 0)

        self.__entry = gtk.Entry(max=0)
        self.__entry.set_visibility(True)
        self.__entry.set_editable(True)
        self.__entry.set_text(value)
        self.pack_start(self.__label, False, False, 0)
        self.pack_start(self.__entry, False, False, 0)

    def get_key(self):
        return self.key

    def get_value(self):
        return self.__entry.get_text()

    def set_value(self, settings, value):
        self.__entry.set_text(value)


class ExtensionCheckBox(gtk.CheckButton):
    def __init__(self, key, settings, value):
        gtk.CheckButton.__init__(self)
        self.set_border_width(6)
        self.key = key

        self.set_label(settings['desc'])
        self.set_active(value)

    def get_key(self):
        return self.key

    def get_value(self):
        return self.get_active()

    def set_value(self, settings, value):
        self.set_active(value)


class ExtensionSpinButton(gtk.VBox):
    def __init__(self, key, settings, value):
        gtk.VBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.key = key

        self.__label = gtk.Label(settings['desc'])
        self.__label.set_alignment(0, 0)

        self.__spin = gtk.SpinButton(
                    adjustment=gtk.Adjustment(value, 0, 1000, 1),
                    climb_rate=1, digits=2
        )

        self.pack_start(self.__label, False, False, 0)
        self.pack_start(self.__spin, False, False, 0)

    def get_key(self):
        return self.key

    def get_value(self):
        return self.__spin.get_value()

    def set_value(self, settings, value):
        self.__spin.set_value(value)


class ExtensionMultiChoice(gtk.VBox):
    def __init__(self, key, settings, value):
        gtk.VBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.key = key

        self.__label = gtk.Label(settings['desc'])
        self.__label.set_alignment(0, 0)

        self.__treeView = gtk.TreeView(self._get_model(settings, value))

        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect('toggled', self.value_changed, self.__treeView)
        toggle_column = gtk.TreeViewColumn('', toggle_cell, active=0)
        toggle_column.set_clickable(True)
        self.__treeView.append_column(toggle_column)

        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(_('Podcast'), renderer, markup=1)
        column.set_clickable(False)
        column.set_resizable(True)
        column.set_expand(True)
        self.__treeView.append_column(column)
        self.__treeView.columns_autosize()

        self.pack_start(self.__label, False, False, 0)
        self.pack_start(self.__treeView, False, False, 0)

    def _get_model(self, settings, value):
        model = gtk.ListStore(
            gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_INT
        )

        multichoice_list = zip(value, settings['list'])
        for index, (state, text) in enumerate(multichoice_list):
            model.append(row=(state, text, index))
        return model

    def value_changed(self, cell, path, treeview):
        model = treeview.get_model()
        iter = model.get_iter(path)
        value = model.get_value(iter, 0)
        model.set_value(iter, 0, not value)

    def get_key(self):
        return self.key

    def get_value(self):
        model = self.__treeView.get_model()
        result = []
        iter = model.get_iter_first()
        while iter is not None:
            value = model.get_value(iter, 0)
            result.append(value)
            iter = model.iter_next(iter)
        return result

    def set_value(self, settings, value):
        model = self._get_model(settings, value)
        self.__treeView.set_model(model)


class ExtensionRadioGroup(gtk.VBox):
    def __init__(self, key, settings, value):
        gtk.VBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.key = key

        self.__label = gtk.Label(settings['desc'])
        self.__label.set_alignment(0, 0)

        self.__radioButtons = []
        choices = zip(value, settings['list'])
        group = None
        for state, label in choices:
            rb = gtk.RadioButton(group, label, False)
            rb.set_active(state)
            group = rb
            self.__radioButtons.append(rb)

        self.pack_start(self.__label, False, False, 0)
        for rb in self.__radioButtons:
            self.pack_start(rb, False, False, 0)

    def get_key(self):
        return self.key

    def get_value(self):
        values = []
        for rb in self.__radioButtons:
            values.append(rb.get_active())
        return values

    def set_value(self, settings, value):
        choices = zip(value, self.__radioButtons)
        for state, rb in choices:
            rb.set_active(state)


#TODO: Replace this implementation with a ComboBoxEntry or expandable TreeView
class ExtensionComboBoxEntry(ExtensionTextItem):
    def __init__(self, key, settings, value):
        value = ';'.join(value)
        ExtensionTextItem.__init__(self, key, settings, value)

    def get_value(self):
        value = super(ExtensionComboBoxEntry, self).get_value()
        return value.split(';')

    def set_value(self, settings, value):
        value = ';'.join(value)
        super(ExtensionComboBoxEntry, self).set_value(settings, value)


class gPodderExtensionPreference(BuilderWidget):
    widgets = { 'textitem': ExtensionTextItem,
        'checkbox': ExtensionCheckBox,
        'spinbutton': ExtensionSpinButton,
        'multichoice-list': ExtensionMultiChoice,
        'combobox': ExtensionComboBoxEntry,
        'radiogroup': ExtensionRadioGroup,
    }

    def new(self):
        """Extension Preference Dialog

        Optional keyword arguments that modify the behaviour of this dialog:

        - _extenstion_consumer: ExtensionConsumer class for which the preferences should be displayed
            {'cmd': {
                'type': 'str',
                'desc': 'Defines the command line bittorrent program'}
            }
        """
        self.params = self._extension_consumer.params
        self.config = self._extension_consumer.config

        self.vbox = gtk.VBox()
        self.viewport_extensionpref.add(self.vbox)
        for key, settings in self.params.items():
            value = getattr(self._extension_consumer.config, key)
            widget = self.widgets[settings['type']](key, settings, value)
            self.vbox.pack_start(widget, False, False, 0)

        self.gPodderExtensionPreference.show_all()

    def on_btnRevert_clicked(self, widget):
        self._extension_consumer.revert_settings()
        self.config = self._extension_consumer.config

        for w in self.vbox.get_children():
            key = w.get_key()
            value = getattr(self._extension_consumer.config, key)
            w.set_value(self.params[key], value)

    def on_btnClose_clicked(self, widget):
        for w in self.vbox.get_children():
            key = w.get_key()
            value = w.get_value()
            setattr(self.config, key, value)

        self.main_window.destroy()


class gPodderExtensionManager(BuilderWidget):
    C_INDEX, C_TOOLTIP, C_TOGGLE, C_NAME, C_ID, C_EXTENSIONCONSUMER = range(6)

    def new(self):
        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect('toggled', self.toggle_cell_handler)
        toggle_column = gtk.TreeViewColumn('', toggle_cell, active=self.C_TOGGLE)
        toggle_column.set_clickable(True)
        self.treeviewExtensions.append_column(toggle_column)

        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(_('Name'), renderer, markup=self.C_NAME)
        column.set_clickable(False)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeviewExtensions.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Extension-ID'), renderer, markup=self.C_ID)
        column.set_clickable(False)
        column.set_resizable(True)
        column.set_expand(False)
        self.treeviewExtensions.append_column(column)

        self.treeviewExtensions.set_property('has-tooltip', True)
        self.treeviewExtensions.connect('query-tooltip', self.treeview_show_tooltip)

        column_types = [ gobject.TYPE_INT,
            gobject.TYPE_STRING,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_PYOBJECT ]
        self.model = gtk.ListStore(*column_types)

        for index, (extension_consumer, state) in enumerate( gpodder.user_extensions.get_extensions() ):
            if extension_consumer.extension_file is not None:
                tooltip = extension_consumer.metadata['desc']
                name = extension_consumer.metadata['name']
                row = [ index, tooltip, state, name,
                    extension_consumer.metadata['id'], extension_consumer
                ]
                self.model.append(row)

        self.model.set_sort_column_id(self.C_NAME, gtk.SORT_ASCENDING)
        self.treeviewExtensions.set_model(self.model)
        self.treeviewExtensions.columns_autosize()

        self.context_id = self.extension_statusbar.get_context_id('Extension messages')

    def _set_enabled_extension_in_config(self, model, path):
        iter = model.get_iter(path)
        value = model.get_value(iter, self.C_TOGGLE)
        name = model.get_value(iter, self.C_NAME)
        extension_id = model.get_value(iter, self.C_ID)
        extension_consumer = model.get_value(iter, self.C_EXTENSIONCONSUMER)
        new_value = not value

        if new_value and extension_id not in self._config.extensions.enabled:
            error = extension_consumer.load_extension()
            if error is None:
                self._config.extensions.enabled.append(extension_id)
                self.extension_statusbar.remove_all(self.context_id)
            else:
                self.extension_statusbar.push(self.context_id, "Error %s: %s" % (name, error))
                return

        if not new_value and extension_id in self._config.extensions.enabled:
            self._config.extensions.enabled.remove(extension_id)

        self._config.schedule_save()
        self._set_preferences_button(not value)
        model.set_value(iter, self.C_TOGGLE, not value)

    def _get_selected_extension_consumer(self):
        selection = self.treeviewExtensions.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return None

        return model.get_value(iter, self.C_EXTENSIONCONSUMER)

    def _set_preferences_button(self, value):
        extension = self._get_selected_extension_consumer()

        if extension and extension.params is not None and value:
            self.btnExtensionPrefs.set_sensitive(True)
        else:
            self.btnExtensionPrefs.set_sensitive(False)

    def on_button_close_clicked(self, widget):
        self.main_window.destroy()

    def on_btnOK_clicked(self, widget):
        self.main_window.destroy()

    def on_btnExtensionPrefs_clicked(self, widget):
        gPodderExtensionPreference(self.main_window,
            _extension_consumer = self._get_selected_extension_consumer()
        )

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

        self._set_preferences_button(value)

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
