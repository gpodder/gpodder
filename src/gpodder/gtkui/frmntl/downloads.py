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
import hildon

import gpodder

_ = gpodder.gettext

from gpodder.download import DownloadTask

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderDownloads(BuilderWidget):
    def new(self):
        self._selected_tasks = []
        selection = self.treeview.get_selection()
        selection.connect('changed', self.on_selection_changed)

        appmenu = hildon.AppMenu()
        for action in (self.action_pause, \
                       self.action_resume, \
                       self.action_cancel, \
                       self.action_cleanup):
            button = gtk.Button()
            action.connect_proxy(button)
            appmenu.append(button)

        for action in (self.action_select_all, \
                       self.action_select_none):
            button = gtk.Button()
            action.connect_proxy(button)
            appmenu.append(button)

        appmenu.show_all()
        self.main_window.set_app_menu(appmenu)

    def on_selection_changed(self, selection):
        selected_tasks, can_queue, can_cancel, can_pause, can_remove, can_force = self.downloads_list_get_selection()
        self._selected_tasks = selected_tasks
        if selected_tasks:
            self.action_pause.set_sensitive(can_pause)
            self.action_resume.set_sensitive(can_queue)
            self.action_cancel.set_sensitive(can_cancel)
        else:
            self.action_pause.set_sensitive(False)
            self.action_resume.set_sensitive(False)
            self.action_cancel.set_sensitive(False)

    def on_delete_event(self, widget, event):
        self.main_window.hide()
        return True

    def show(self):
        self.main_window.show()

    def on_pause_button_clicked(self, button):
        self._for_each_task_set_status(self._selected_tasks, DownloadTask.PAUSED)
        self.on_select_none_button_clicked(button)

    def on_resume_button_clicked(self, button):
        self._for_each_task_set_status(self._selected_tasks, DownloadTask.QUEUED)
        self.on_select_none_button_clicked(button)

    def on_cancel_button_clicked(self, button):
        self._for_each_task_set_status(self._selected_tasks, DownloadTask.CANCELLED)
        self.on_select_none_button_clicked(button)

    def on_cleanup_button_clicked(self, button):
        self.cleanup_downloads()

    def on_select_all_button_clicked(self, button):
        selection = self.treeview.get_selection()
        selection.select_all()

    def on_select_none_button_clicked(self, button):
        selection = self.treeview.get_selection()
        selection.unselect_all()

