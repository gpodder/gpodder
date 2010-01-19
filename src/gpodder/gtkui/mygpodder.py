# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

# gpodder.gtkui.mygpodder- UI code for my.gpodder.org settings
# Thomas Perl <thpinfo.com>; 2010-01-19

import gtk

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget

class MygPodderSettings(BuilderWidget):
    # Valid types defined in mygpoclient.api.PodcastDevice
    VALID_TYPES = (
            ('desktop', _('Desktop')),
            ('laptop', _('Laptop')),
            ('mobile', _('Mobile phone')),
            ('server', _('Server')),
            ('other', _('Other')),
    )

    # Columns IDs for the combo box model
    C_ID, C_CAPTION = range(2)

    def new(self):
        active_index = 0
        self._model = gtk.ListStore(str, str)
        for index, data in enumerate(self.VALID_TYPES):
            id, caption = data
            if id == self.config.mygpo_device_type:
                active_index = index
            self._model.append(data)
        self.combo_type.set_model(self._model)

        cell = gtk.CellRendererText()
        self.combo_type.pack_start(cell, True)
        self.combo_type.add_attribute(cell, 'text', 1)

        # Initialize the UI state with configuration settings
        self.checkbutton_enable.set_active(self.config.mygpo_enabled)
        self.entry_username.set_text(self.config.mygpo_username)
        self.entry_password.set_text(self.config.mygpo_password)
        self.entry_uid.set_text(self.config.mygpo_device_uid)
        self.entry_caption.set_text(self.config.mygpo_device_caption)
        self.combo_type.set_active(active_index)

    def on_button_list_uids_clicked(self, button):
        # FIXME: Not implemented yet
        pass

    def on_button_cancel_clicked(self, button):
        # Ignore changed settings and close
        self.main_window.destroy()

    def on_button_save_clicked(self, button):
        model = self.combo_type.get_model()
        it = self.combo_type.get_active_iter()
        device_type = model.get_value(it, self.C_ID)

        # Update configuration and close
        self.config.mygpo_enabled = self.checkbutton_enable.get_active()
        self.config.mygpo_username = self.entry_username.get_text()
        self.config.mygpo_password = self.entry_password.get_text()
        self.config.mygpo_device_uid = self.entry_uid.get_text()
        self.config.mygpo_device_caption = self.entry_caption.get_text()
        self.config.mygpo_device_type = device_type

        self.main_window.destroy()


