# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

import os

from gi.repository import Gdk, Gtk

import gpodder
from gpodder import util
from gpodder.gtkui.base import GtkBuilderWidget

_ = gpodder.gettext


def show_message_dialog(parent, message, title=None):
    dlg = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.OK)
    if title:
        dlg.set_title(title)
        dlg.set_property('text', title)
        dlg.format_secondary_text(message)
    else:
        dlg.set_property('text', message)
    # make message copy/pastable
    for lbl in dlg.get_message_area():
        if isinstance(lbl, Gtk.Label):
            lbl.set_selectable(True)
    dlg.run()
    dlg.destroy()


class BuilderWidget(GtkBuilderWidget):
    def __init__(self, parent, **kwargs):
        self._window_iconified = False

        GtkBuilderWidget.__init__(self, gpodder.ui_folders, gpodder.textdomain, parent, **kwargs)

        # Enable support for tracking iconified state
        if hasattr(self, 'on_iconify') and hasattr(self, 'on_uniconify'):
            self.main_window.connect('window-state-event',
                    self._on_window_state_event_iconified)

    def _on_window_state_event_iconified(self, widget, event):
        if event.new_window_state & Gdk.WindowState.ICONIFIED:
            if not self._window_iconified:
                self._window_iconified = True
                self.on_iconify()
        else:
            if self._window_iconified:
                self._window_iconified = False
                self.on_uniconify()

        return False

    def is_iconified(self):
        return self._window_iconified

    def notification(self, message, title=None, important=False, widget=None):
        util.idle_add(self.show_message, message, title, important, widget)

    def get_dialog_parent(self):
        """Return a Gtk.Window that should be the parent of dialogs"""
        return self.main_window

    def show_message_details(self, title, message, details):
        dlg = Gtk.MessageDialog(self.main_window, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.OK)
        dlg.set_title(title)
        dlg.set_property('text', title)
        dlg.format_secondary_text(message)

        # make message copy/pastable
        for lbl in dlg.get_message_area():
            if isinstance(lbl, Gtk.Label):
                lbl.set_halign(Gtk.Align.START)
                lbl.set_selectable(True)

        tv = Gtk.TextView()
        tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        tv.set_border_width(10)
        tv.set_editable(False)
        tb = Gtk.TextBuffer()
        tb.insert_markup(tb.get_start_iter(), details, -1)
        tv.set_buffer(tb)
        tv.set_property('expand', True)
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(400, 200)
        sw.set_property('shadow-type', Gtk.ShadowType.IN)
        sw.add(tv)
        sw.show_all()

        dlg.get_message_area().add(sw)
        dlg.get_widget_for_response(Gtk.ResponseType.OK).grab_focus()
        dlg.run()
        dlg.destroy()

    def show_message(self, message, title=None, important=False, widget=None):
        if important:
            show_message_dialog(self.main_window, message, title)
        else:
            gpodder.user_extensions.on_notification_show(title, message)

    def show_confirmation(self, message, title=None):
        dlg = Gtk.MessageDialog(self.main_window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO)
        if title:
            dlg.set_title(str(title))
            dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
        else:
            dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
        response = dlg.run()
        dlg.destroy()
        return response == Gtk.ResponseType.YES

    def show_text_edit_dialog(self, title, prompt, text=None, empty=False,
            is_url=False, affirmative_text=_('_OK')):
        dialog = Gtk.Dialog(title, self.get_dialog_parent(),
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)

        dialog.add_button(_('_Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(affirmative_text, Gtk.ResponseType.OK)

        dialog.set_default_size(300, -1)
        dialog.set_default_response(Gtk.ResponseType.OK)

        text_entry = Gtk.Entry()
        text_entry.set_activates_default(True)
        if text is not None:
            text_entry.set_text(text)
            text_entry.select_region(0, -1)

        if not empty:
            def on_text_changed(editable):
                can_confirm = (editable.get_text() != '')
                dialog.set_response_sensitive(Gtk.ResponseType.OK, can_confirm)
            text_entry.connect('changed', on_text_changed)
            if text is None:
                dialog.set_response_sensitive(Gtk.ResponseType.OK, False)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(10)
        hbox.set_spacing(10)
        hbox.pack_start(Gtk.Label(prompt, True, True, 0), False, False, 0)
        hbox.pack_start(text_entry, True, True, 0)
        dialog.vbox.pack_start(hbox, True, True, 0)

        dialog.show_all()
        response = dialog.run()
        result = text_entry.get_text()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            return result
        else:
            return None

    def show_login_dialog(self, title, message, root_url=None, username=None, password=None,
            username_prompt=None, register_callback=None, register_text=None, ask_server=False):
        def toggle_password_visibility(_, entry):
            entry.set_visibility(not entry.get_visibility())

        if username_prompt is None:
            username_prompt = _('Username')

        if register_text is None:
            register_text = _('New user')

        dialog = Gtk.MessageDialog(
            self.main_window,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.CANCEL)
        dialog.add_button(_('Login'), Gtk.ResponseType.OK)
        dialog.set_image(Gtk.Image.new_from_icon_name('dialog-password', Gtk.IconSize.DIALOG))
        dialog.set_title(_('Authentication required'))
        dialog.set_markup('<span weight="bold" size="larger">' + title + '</span>')
        dialog.format_secondary_markup(message)
        dialog.set_default_response(Gtk.ResponseType.OK)

        if register_callback is not None:
            dialog.add_button(register_text, Gtk.ResponseType.HELP)

        server_entry = Gtk.Entry()
        server_entry.set_tooltip_text(_('hostname or root URL (e.g. https://gpodder.net)'))
        username_entry = Gtk.Entry()
        password_entry = Gtk.Entry()

        server_entry.connect('activate', lambda w: username_entry.grab_focus())
        username_entry.connect('activate', lambda w: password_entry.grab_focus())
        password_entry.set_visibility(False)
        password_entry.set_activates_default(True)

        if root_url is not None:
            server_entry.set_text(root_url)
        if username is not None:
            username_entry.set_text(username)
        if password is not None:
            password_entry.set_text(password)

        table = Gtk.Table(3, 2)
        table.set_row_spacings(6)
        table.set_col_spacings(6)

        server_label = Gtk.Label()
        server_label.set_markup('<b>' + _('Server') + ':</b>')

        username_label = Gtk.Label()
        username_label.set_markup('<b>' + username_prompt + ':</b>')

        password_label = Gtk.Label()
        password_label.set_markup('<b>' + _('Password') + ':</b>')

        show_password_label = Gtk.Label()
        show_password = Gtk.CheckButton.new_with_label(_('Show Password'))
        show_password.connect('toggled', toggle_password_visibility, password_entry)

        label_entries = [(username_label, username_entry),
                         (password_label, password_entry),
                         (show_password_label, show_password)]

        if ask_server:
            label_entries.insert(0, (server_label, server_entry))

        for i, (label, entry) in enumerate(label_entries):
            label.set_alignment(0.0, 0.5)
            table.attach(label, 0, 1, i, i + 1, Gtk.AttachOptions.FILL, 0)
            table.attach(entry, 1, 2, i, i + 1)

        dialog.vbox.pack_end(table, True, True, 0)
        dialog.show_all()
        username_entry.grab_focus()
        response = dialog.run()

        while response == Gtk.ResponseType.HELP:
            register_callback()
            response = dialog.run()

        password_entry.set_visibility(True)
        root_url = server_entry.get_text()
        username = username_entry.get_text()
        password = password_entry.get_text()
        success = (response == Gtk.ResponseType.OK)

        dialog.destroy()

        if ask_server:
            return (success, (root_url, username, password))
        else:
            return (success, (username, password))

    def show_folder_select_dialog(self, initial_directory=None, title=_('Select destination')):
        if initial_directory is None:
            initial_directory = os.path.expanduser('~')

        dlg = Gtk.FileChooserDialog(title=title, parent=self.main_window, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_button(_('_Cancel'), Gtk.ResponseType.CANCEL)
        dlg.add_button(_('_Save'), Gtk.ResponseType.OK)

        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_folder(initial_directory)

        result = False
        folder = initial_directory
        if dlg.run() == Gtk.ResponseType.OK:
            result = True
            folder = dlg.get_current_folder()

        dlg.destroy()
        return (result, folder)


class TreeViewHelper(object):
    """Container for gPodder-specific TreeView attributes."""
    LAST_TOOLTIP = '_gpodder_last_tooltip'
    CAN_TOOLTIP = '_gpodder_can_tooltip'
    ROLE = '_gpodder_role'
    COLUMNS = '_gpodder_columns'

    # Enum for the role attribute
    ROLE_PODCASTS, ROLE_EPISODES, ROLE_DOWNLOADS = list(range(3))

    @classmethod
    def set(cls, treeview, role):
        setattr(treeview, cls.LAST_TOOLTIP, None)
        setattr(treeview, cls.CAN_TOOLTIP, True)
        setattr(treeview, cls.ROLE, role)

    @staticmethod
    def make_search_equal_func(gpodder_model):
        def func(model, column, key, iter):
            if model is None:
                return True
            key = key.lower()
            for column in gpodder_model.SEARCH_COLUMNS:
                if key in model.get_value(iter, column).lower():
                    return False
            return True
        return func

    @classmethod
    def register_column(cls, treeview, column):
        if not hasattr(treeview, cls.COLUMNS):
            setattr(treeview, cls.COLUMNS, [])

        columns = getattr(treeview, cls.COLUMNS)
        columns.append(column)

    @classmethod
    def get_columns(cls, treeview):
        return getattr(treeview, cls.COLUMNS, [])

    @staticmethod
    def make_popup_position_func(widget):
        """
        :return: suitable function to pass to Gtk.Menu.popup()
        It's used for instance when the popup trigger is the Menu key:
        it will position the menu on top of the selected row even if the mouse is elsewhere
        see http://lazka.github.io/pgi-docs/#Gtk-3.0/classes/Menu.html#Gtk.Menu.popup
        """
        def position_func(menu, *unused_args):
            _, x, y = widget.get_bin_window().get_origin()

            # If there's a selection, place the popup menu on top of
            # the first-selected row (otherwise in the top left corner)
            selection = widget.get_selection()
            model, paths = selection.get_selected_rows()
            if paths:
                path = paths[0]
                area = widget.get_cell_area(path, widget.get_column(0))
                x += area.x
                y += area.y

            return (x, y, True)
        return position_func
