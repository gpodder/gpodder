# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

# gpodder.gtkui.mygpodder- UI code for gpodder.net settings
# Thomas Perl <thp@gpodder.org>; 2010-01-19

import threading

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget


class MygPodderSettings(BuilderWidget):
    # Columns IDs for the combo box model
    C_ID, C_CAPTION = range(2)

    def new(self):
        # We need to have a MygPoClient instance available
        assert getattr(self, 'mygpo_client', None) is not None

        active_index = 0

        # Initialize the UI state with configuration settings
        self.checkbutton_enable.set_active(self.config.mygpo_enabled)
        self.entry_username.set_text(self.config.mygpo_username)
        self.entry_password.set_text(self.config.mygpo_password)
        #self.label_uid_value.set_label(self.config.mygpo_device_uid)
        self.entry_caption.set_text(self.config.mygpo_device_caption)

        # Disable input capitalization for the login fields
        self.entry_username.set_property('hildon-input-mode', \
                    'HILDON_GTK_INPUT_MODE_FULL')
        self.entry_password.set_property('hildon-input-mode', \
                    'HILDON_GTK_INPUT_MODE_FULL')
        self.entry_password.set_visibility(False)

        # Disable mygpo sync while the dialog is open
        self._enable_mygpo = self.config.mygpo_enabled
        self.config.mygpo_enabled = False

    def on_enabled_toggled(self, widget):
        # Only update indirectly (see on_delete_event)
        self._enable_mygpo = widget.get_active()

    def on_username_changed(self, widget):
        self.config.mygpo_username = widget.get_text()

    def on_password_changed(self, widget):
        self.config.mygpo_password = widget.get_text()

    def on_device_caption_changed(self, widget):
        self.config.mygpo_device_caption = widget.get_text()

    def on_button_overwrite_clicked(self, button):
        title = _('Replace subscription list on server')
        message = _('Remote podcasts that have not been added locally will be removed on the server. Continue?')
        if self.show_confirmation(message, title):
            def thread_proc():
                self.config.mygpo_enabled = True
                self.on_send_full_subscriptions()
                self.config.mygpo_enabled = False
            threading.Thread(target=thread_proc).start()

    def on_delete_event(self, widget, event):
        # Re-enable mygpo sync if the user has selected it
        self.config.mygpo_enabled = self._enable_mygpo
        # Make sure the device is successfully created/updated
        self.mygpo_client.create_device()
        # Flush settings for mygpo client now
        self.mygpo_client.flush(now=True)

    def on_button_close_clicked(self, button):
        self.on_delete_event(self.main_window, None)
        self.main_window.destroy()

