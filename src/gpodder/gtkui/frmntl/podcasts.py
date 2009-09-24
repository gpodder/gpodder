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

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.model import PodcastListModel

class gPodderPodcasts(BuilderWidget):
    def new(self):
        appmenu = hildon.AppMenu()
        #for action in (self.action_update_feeds,):
        #    button = gtk.Button()
        #    action.connect_proxy(button)
        #    appmenu.append(button)
        for filter in (self.item_view_podcasts_all, \
                       self.item_view_podcasts_downloaded, \
                       self.item_view_podcasts_unplayed):
            button = gtk.ToggleButton()
            filter.connect_proxy(button)
            appmenu.add_filter(button)
        appmenu.show_all()
        self.main_window.set_app_menu(appmenu)

    def on_update_feeds_button_clicked(self, button):
        self.main_window.hide()
        util.idle_add(self.on_itemUpdate_activate, button)

    def on_podcast_selected(self, treeview, path, column):
        model = treeview.get_model()
        channel = model.get_value(model.get_iter(path), \
                PodcastListModel.C_CHANNEL)
        self.show_podcast_episodes(channel)

    def on_delete_event(self, widget, event):
        self.main_window.hide()
        return True

    def show(self):
        self.main_window.show()

