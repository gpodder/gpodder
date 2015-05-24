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

import gtk
import cgi

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.config import ConfigModel

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderConfigEditor(BuilderWidget):
    def new(self):
        name_column = gtk.TreeViewColumn(_('Setting'))
        name_renderer = gtk.CellRendererText()
        name_column.pack_start(name_renderer)
        name_column.add_attribute(name_renderer, 'text', 0)
        name_column.add_attribute(name_renderer, 'style', 5)
        self.configeditor.append_column(name_column)

        value_column = gtk.TreeViewColumn(_('Set to'))
        value_check_renderer = gtk.CellRendererToggle()
        value_column.pack_start(value_check_renderer, expand=False)
        value_column.add_attribute(value_check_renderer, 'active', 7)
        value_column.add_attribute(value_check_renderer, 'visible', 6)
        value_column.add_attribute(value_check_renderer, 'activatable', 6)
        value_check_renderer.connect('toggled', self.value_toggled)

        value_renderer = gtk.CellRendererText()
        value_column.pack_start(value_renderer)
        value_column.add_attribute(value_renderer, 'text', 2)
        value_column.add_attribute(value_renderer, 'visible', 4)
        value_column.add_attribute(value_renderer, 'editable', 4)
        value_column.add_attribute(value_renderer, 'style', 5)
        value_renderer.connect('edited', self.value_edited)
        self.configeditor.append_column(value_column)

        self.model = ConfigModel(self._config)
        self.filter = self.model.filter_new()
        self.filter.set_visible_func(self.visible_func)

        self.configeditor.set_model(self.filter)
        self.configeditor.set_rules_hint(True)

    def visible_func(self, model, iter, user_data=None):
        text = self.entryFilter.get_text().lower()
        if text == '':
            return True
        else:
            # either the variable name or its value
            return (text in model.get_value(iter, 0).lower() or
                    text in model.get_value(iter, 2).lower())

    def value_edited(self, renderer, path, new_text):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        name = model.get_value(iter, 0)
        type_cute = model.get_value(iter, 1)

        if not self._config.update_field(name, new_text):
            message = _('Cannot set %(field)s to %(value)s. Needed data type: %(datatype)s')
            d = {'field': cgi.escape(name),
                 'value': cgi.escape(new_text),
                 'datatype': cgi.escape(type_cute)}
            self.notification(message % d, _('Error setting option'))

    def value_toggled(self, renderer, path):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        field_name = model.get_value(iter, 0)
        field_type = model.get_value(iter, 3)

        # Flip the boolean config flag
        if field_type == bool:
            self._config.toggle_flag(field_name)
    
    def on_entryFilter_changed(self, widget):
        self.filter.refilter()

    def on_btnShowAll_clicked(self, widget):
        self.entryFilter.set_text('')
        self.entryFilter.grab_focus()

    def on_btnClose_clicked(self, widget):
        self.gPodderConfigEditor.destroy()

    def on_gPodderConfigEditor_destroy(self, widget):
        self.model.stop_observing()

