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
import threading

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.progress import ProgressIndicator
from gpodder.gtkui.interface.common import BuilderWidget


class DeviceList(gtk.ListStore):
    C_UID, C_CAPTION, C_DEVICE_TYPE, C_ICON_NAME = range(4)

    def __init__(self, devices):
        gtk.ListStore.__init__(self, str, str, str, str)
        for uid, caption, device_type in devices:
            if device_type == 'desktop':
                icon_name = 'computer'
            elif device_type == 'mobile':
                icon_name = 'phone'
            elif device_type == 'server':
                icon_name = 'server'
            elif device_type == 'laptop':
                icon_name = 'stock_notebook'
            else:
                icon_name = 'audio-x-generic'
            self.append((uid, caption, device_type, icon_name))

class DeviceBrowser(gtk.Dialog):
    def __init__(self, model, parent=None):
        gtk.Dialog.__init__(self, _('Select a device'), parent)

        self._model = model

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        hbox.set_spacing(6)
        self.vbox.add(hbox)
        hbox.pack_start(gtk.Label(_('Device:')), expand=False)

        combobox = gtk.ComboBox()
        hbox.add(combobox)
        cell = gtk.CellRendererPixbuf()
        combobox.pack_start(cell, expand=False)
        combobox.add_attribute(cell, 'icon-name', DeviceList.C_ICON_NAME)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell)
        combobox.add_attribute(cell, 'text', DeviceList.C_CAPTION)

        combobox.set_model(self._model)
        combobox.set_active(0)
        self._combobox = combobox

        self.add_button(_('Cancel'), gtk.RESPONSE_CANCEL)
        self.add_button(_('Use device'), gtk.RESPONSE_OK)

    def get_selected(self):
        result = None

        self.show_all()
        if self.run() == gtk.RESPONSE_OK:
            active = self._combobox.get_active()
            result = (self._model[active][DeviceList.C_UID],
                      self._model[active][DeviceList.C_CAPTION],
                      self._model[active][DeviceList.C_DEVICE_TYPE])
        self.destroy()

        return result


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
        # We need to have a MygPoClient instance available
        assert getattr(self, 'mygpo_client', None) is not None

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

        self.button_overwrite.set_sensitive(True)

    def on_device_settings_changed(self, widget):
        self.button_overwrite.set_sensitive(False)

    def on_button_overwrite_clicked(self, button):
        threading.Thread(target=self.mygpo_client.force_fresh_upload).start()

    def on_button_list_uids_clicked(self, button):
        indicator = ProgressIndicator(_('Downloading device list'),
                _('Getting the list of devices from your account.'),
                False, self.main_window)

        def thread_proc():
            devices = self.mygpo_client.get_devices()
            indicator.on_finished()
            def ui_callback(devices):
                model = DeviceList(devices)
                dialog = DeviceBrowser(model, self.main_window)
                result = dialog.get_selected()
                if result is not None:
                    uid, caption, device_type = result
                    self.entry_uid.set_text(uid)
                    self.entry_caption.set_text(caption)
                    for index, data in enumerate(self.VALID_TYPES):
                        d_type, d_name = data
                        if device_type == d_type:
                            self.combo_type.set_active(index)
                            break
            util.idle_add(ui_callback, devices)

        threading.Thread(target=thread_proc).start()

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

