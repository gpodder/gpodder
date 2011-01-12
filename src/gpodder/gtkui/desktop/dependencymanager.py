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

import gpodder

_ = gpodder.gettext

from gpodder import services

from gpodder.gtkui.services import DependencyModel

from gpodder.gtkui.interface.common import BuilderWidget

class gPodderDependencyManager(BuilderWidget):
    def new(self):
        col_name = gtk.TreeViewColumn(_('Feature'), gtk.CellRendererText(), text=0)
        self.treeview_components.append_column(col_name)
        col_installed = gtk.TreeViewColumn(_('Status'), gtk.CellRendererText(), text=2)
        self.treeview_components.append_column(col_installed)
        self.treeview_components.set_model(DependencyModel(services.dependency_manager))
        self.btn_about.set_sensitive(False)
        self.btn_install.hide()

    def on_btn_about_clicked(self, widget):
        selection = self.treeview_components.get_selection()
        model, iter = selection.get_selected()
        if iter is not None:
            title = model.get_value(iter, 0)
            description = model.get_value(iter, 1)
            available = model.get_value(iter, 3)
            missing = model.get_value(iter, 4)

            if not available:
                description += '\n\n'+_('Missing components:')+'\n\n'+missing

            self.show_message(description, title, important=True)

    def on_btn_install_clicked(self, widget):
        # TODO: Implement package manager integration
        pass

    def on_treeview_components_cursor_changed(self, treeview):
        self.btn_about.set_sensitive(treeview.get_selection().count_selected_rows() > 0)
        # TODO: If installing is possible, show btn_install

    def on_gPodderDependencyManager_response(self, dialog, response_id):
        self.gPodderDependencyManager.destroy()

