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

import gtk
import hildon

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderDownloads(BuilderWidget):
    def new(self):
        appmenu = hildon.AppMenu()
        for action in (self.action_pause, \
                       self.action_resume, \
                       self.action_cancel, \
                       self.action_cleanup, \
                       self.action_select_all, \
                       self.action_select_none):
            button = gtk.Button()
            action.connect_proxy(button)
            appmenu.append(button)
        appmenu.show_all()
        self.main_window.set_app_menu(appmenu)
        # Work around Maemo bug #4718
        #self.button_subscribe.set_name('HildonButton-finger')

    def on_delete_event(self, widget, event):
        self.main_window.hide()
        return True

    def show(self):
        self.main_window.show()

    def on_pause_button_clicked(self, button):
        pass

    def on_resume_button_clicked(self, button):
        pass

    def on_cancel_button_clicked(self, button):
        pass

    def on_cleanup_button_clicked(self, button):
        self.on_btnCleanUpDownloads_clicked(button)

    def on_select_all_button_clicked(self, button):
        selection = self.treeview.get_selection()
        selection.select_all()

    def on_select_none_button_clicked(self, button):
        selection = self.treeview.get_selection()
        selection.unselect_all()

