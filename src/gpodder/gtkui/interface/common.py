# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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
import os
import shutil

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.base import GtkBuilderWidget


class BuilderWidget(GtkBuilderWidget):
    def __init__(self, parent, **kwargs):
        self._window_iconified = False
        self._window_visible = False

        GtkBuilderWidget.__init__(self, gpodder.ui_folders, gpodder.textdomain, **kwargs)

        # Enable support for tracking iconified state
        if hasattr(self, 'on_iconify') and hasattr(self, 'on_uniconify'):
            self.main_window.connect('window-state-event', \
                    self._on_window_state_event_iconified)

        # Enable support for tracking visibility state
        self.main_window.connect('visibility-notify-event', \
                    self._on_window_state_event_visibility)

        if parent is not None:
            self.main_window.set_transient_for(parent)

            if hasattr(self, 'center_on_widget'):
                (x, y) = parent.get_position()
                a = self.center_on_widget.allocation
                (x, y) = (x + a.x, y + a.y)
                (w, h) = (a.width, a.height)
                (pw, ph) = self.main_window.get_size()
                self.main_window.move(x + w/2 - pw/2, y + h/2 - ph/2)

    def _on_window_state_event_visibility(self, widget, event):
        if event.state & gtk.gdk.VISIBILITY_FULLY_OBSCURED:
            self._window_visible = False
        else:
            self._window_visible = True

        return False

    def _on_window_state_event_iconified(self, widget, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
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
        """Return a gtk.Window that should be the parent of dialogs"""
        return self.main_window

    def show_message(self, message, title=None, important=False, widget=None):
        if important:
            dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
            if title:
                dlg.set_title(str(title))
                dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
            else:
                dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
            dlg.run()
            dlg.destroy()
        else:
            gpodder.user_extensions.on_notification_show(title, message)

    def show_confirmation(self, message, title=None):
        dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
        if title:
            dlg.set_title(str(title))
            dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
        else:
            dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
        response = dlg.run()
        dlg.destroy()
        return response == gtk.RESPONSE_YES

    def show_text_edit_dialog(self, title, prompt, text=None, empty=False, \
            is_url=False, affirmative_text=gtk.STOCK_OK):
        dialog = gtk.Dialog(title, self.get_dialog_parent(), \
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)

        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(affirmative_text, gtk.RESPONSE_OK)

        dialog.set_has_separator(False)
        dialog.set_default_size(300, -1)
        dialog.set_default_response(gtk.RESPONSE_OK)

        text_entry = gtk.Entry()
        text_entry.set_activates_default(True)
        if text is not None:
            text_entry.set_text(text)
            text_entry.select_region(0, -1)

        if not empty:
            def on_text_changed(editable):
                can_confirm = (editable.get_text() != '')
                dialog.set_response_sensitive(gtk.RESPONSE_OK, can_confirm)
            text_entry.connect('changed', on_text_changed)
            if text is None:
                dialog.set_response_sensitive(gtk.RESPONSE_OK, False)

        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.set_spacing(10)
        hbox.pack_start(gtk.Label(prompt), False, False)
        hbox.pack_start(text_entry, True, True)
        dialog.vbox.pack_start(hbox, True, True)

        dialog.show_all()
        response = dialog.run()
        result = text_entry.get_text()
        dialog.destroy()

        if response == gtk.RESPONSE_OK:
            return result
        else:
            return None

    def show_login_dialog(self, title, message, username=None, password=None,
            username_prompt=None, register_callback=None, register_text=None):
        if username_prompt is None:
            username_prompt = _('Username')

        if register_text is None:
            register_text = _('New user')

        dialog = gtk.MessageDialog(
            self.main_window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_CANCEL)
        dialog.add_button(_('Login'), gtk.RESPONSE_OK)
        dialog.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_DIALOG))
        dialog.set_title(_('Authentication required'))
        dialog.set_markup('<span weight="bold" size="larger">' + title + '</span>')
        dialog.format_secondary_markup(message)
        dialog.set_default_response(gtk.RESPONSE_OK)

        if register_callback is not None:
            dialog.add_button(register_text, gtk.RESPONSE_HELP)

        username_entry = gtk.Entry()
        password_entry = gtk.Entry()

        username_entry.connect('activate', lambda w: password_entry.grab_focus())
        password_entry.set_visibility(False)
        password_entry.set_activates_default(True)

        if username is not None:
            username_entry.set_text(username)
        if password is not None:
            password_entry.set_text(password)

        table = gtk.Table(2, 2)
        table.set_row_spacings(6)
        table.set_col_spacings(6)

        username_label = gtk.Label()
        username_label.set_markup('<b>' + username_prompt + ':</b>')
        username_label.set_alignment(0.0, 0.5)
        table.attach(username_label, 0, 1, 0, 1, gtk.FILL, 0)
        table.attach(username_entry, 1, 2, 0, 1)

        password_label = gtk.Label()
        password_label.set_markup('<b>' + _('Password') + ':</b>')
        password_label.set_alignment(0.0, 0.5)
        table.attach(password_label, 0, 1, 1, 2, gtk.FILL, 0)
        table.attach(password_entry, 1, 2, 1, 2)

        dialog.vbox.pack_end(table, True, True, 0)
        dialog.show_all()
        response = dialog.run()

        while response == gtk.RESPONSE_HELP:
            register_callback()
            response = dialog.run()

        password_entry.set_visibility(True)
        username = username_entry.get_text()
        password = password_entry.get_text()
        success = (response == gtk.RESPONSE_OK)

        dialog.destroy()

        return (success, (username, password))

    def show_copy_dialog(self, src_filename, dst_filename=None, dst_directory=None, title=_('Select destination')):
        if dst_filename is None:
            dst_filename = src_filename

        if dst_directory is None:
            dst_directory = os.path.expanduser('~')

        base, extension = os.path.splitext(src_filename)

        if not dst_filename.endswith(extension):
            dst_filename += extension

        dlg = gtk.FileChooserDialog(title=title, parent=self.main_window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(os.path.basename(dst_filename))
        dlg.set_current_folder(dst_directory)

        result = False
        folder = dst_directory
        if dlg.run() == gtk.RESPONSE_OK:
            result = True
            dst_filename = dlg.get_filename()
            folder = dlg.get_current_folder()
            if not dst_filename.endswith(extension):
                dst_filename += extension

            shutil.copyfile(src_filename, dst_filename)

        dlg.destroy()
        return (result, folder)

class TreeViewHelper(object):
    """Container for gPodder-specific TreeView attributes."""
    LAST_TOOLTIP = '_gpodder_last_tooltip'
    CAN_TOOLTIP = '_gpodder_can_tooltip'
    ROLE = '_gpodder_role'
    COLUMNS = '_gpodder_columns'

    # Enum for the role attribute
    ROLE_PODCASTS, ROLE_EPISODES, ROLE_DOWNLOADS = range(3)

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
        def position_func(menu):
            x, y = widget.get_bin_window().get_origin()

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

