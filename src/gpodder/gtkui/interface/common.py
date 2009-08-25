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
import os
import shutil
import sys

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.base import GtkBuilderWidget

from gpodder.gtkui.widgets import NotificationWindow

try:
    import pynotify
    if pynotify.init('gPodder'):
        pynotify_server_info = pynotify.get_server_info()
        pynotify_server = pynotify_server_info.get('name', 'unknown')
        notify_server_from_canonical = (pynotify_server == 'notify-osd')
        if notify_server_from_canonical:
            print >>sys.stderr, 'Broken libnotify server from Canonical found.'
            print >>sys.stderr, '(notify-osd does not position notifications!)'
    else:
        pynotify = None
        notify_server_from_canonical = False
except ImportError:
    pynotify = None
    notify_server_from_canonical = False

class BuilderWidget(GtkBuilderWidget):
    finger_friendly_widgets = []

    def __init__(self, parent, **kwargs):
        GtkBuilderWidget.__init__(self, gpodder.ui_folder, gpodder.textdomain, **kwargs)

        # Set widgets to finger-friendly mode if on Maemo
        for widget_name in self.finger_friendly_widgets:
            if hasattr(self, widget_name):
                self.set_finger_friendly(getattr(self, widget_name))

        if parent is not None:
            self.main_window.set_transient_for(parent)

            if gpodder.interface == gpodder.GUI:
                if hasattr(self, 'center_on_widget'):
                    (x, y) = parent.get_position()
                    a = self.center_on_widget.allocation
                    (x, y) = (x + a.x, y + a.y)
                    (w, h) = (a.width, a.height)
                    (pw, ph) = self.main_window.get_size()
                    self.main_window.move(x + w/2 - pw/2, y + h/2 - ph/2)
                else:
                    self.main_window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

    def notification(self, message, title=None, important=False, widget=None):
        util.idle_add(self.show_message, message, title, important, widget)

    def show_message(self, message, title=None, important=False, widget=None):
        if gpodder.interface == gpodder.MAEMO:
            import hildon
            if important:
                dlg = hildon.Note('information', (self.main_window, message))
                dlg.run()
                dlg.destroy()
            else:
                if title is None:
                    title = 'gPodder'
                pango_markup = '<b>%s</b>\n<small>%s</small>' % (title, message)
                hildon.hildon_banner_show_information_with_markup(gtk.Label(''), None, pango_markup)
        else:
            if important:
                dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
                if title:
                    dlg.set_title(str(title))
                    dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
                else:
                    dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
                dlg.run()
                dlg.destroy()
            elif pynotify is not None and not notify_server_from_canonical:
                if title is None:
                    title = 'gPodder'
                notification = pynotify.Notification(title, message, gpodder.icon_file)

                if widget and isinstance(widget, gtk.Widget):
                    if not widget.window:
                        widget = self.main_window
                    notification.attach_to_widget(widget)

                notification.show()
            else:
                if widget and isinstance(widget, gtk.Widget):
                    if not widget.window:
                        widget = self.main_window
                else:
                    widget = self.main_window
                notification = NotificationWindow(message, title, important=False, widget=widget)
                notification.show_timeout()

    def set_finger_friendly(self, widget):
        """
        If we are on Maemo, we carry out the necessary
        operations to turn a widget into a finger-friendly
        one, depending on which type of widget it is (i.e.
        buttons will have more padding, TreeViews a thick
        scrollbar, etc..)
        """
        if widget is None:
            return None

        if gpodder.interface == gpodder.MAEMO:
            if isinstance(widget, gtk.Misc):
                widget.set_padding(0, 5)
            elif isinstance(widget, gtk.Button):
                for child in widget.get_children():
                    if isinstance(child, gtk.Alignment):
                        child.set_padding(5, 5, 5, 5)
                    else:
                        child.set_padding(5, 5)
            elif isinstance(widget, gtk.TreeView) or isinstance(widget, gtk.TextView):
                parent = widget.get_parent()
                if isinstance(parent, gtk.ScrolledWindow):
                    import hildon
                    hildon.hildon_helper_set_thumb_scrollbar(parent, True)
            elif isinstance(widget, gtk.MenuItem):
                for child in widget.get_children():
                    self.set_finger_friendly(child)
                submenu = widget.get_submenu()
                if submenu is not None:
                    for child in submenu.get_children():
                        self.set_finger_friendly(child)
            elif isinstance(widget, gtk.Menu):
                for child in widget.get_children():
                    self.set_finger_friendly(child)

        return widget

    def show_confirmation(self, message, title=None):
        if gpodder.interface == gpodder.GUI:
            dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
            if title:
                dlg.set_title(str(title))
                dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
            else:
                dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
            response = dlg.run()
            dlg.destroy()
            return response == gtk.RESPONSE_YES
        elif gpodder.interface == gpodder.MAEMO:
            import hildon
            dlg = hildon.Note('confirmation', (self.main_window, message))
            response = dlg.run()
            dlg.destroy()
            return response == gtk.RESPONSE_OK
        else:
            raise Exception('Unknown interface type')

    def show_login_dialog(self, title, message, username=None, password=None, username_prompt=_('Username'), register_callback=None):
        """ An authentication dialog based on
                http://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/ """

        dialog = gtk.MessageDialog(
            self.main_window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL )

        dialog.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_DIALOG))

        dialog.set_markup('<span weight="bold" size="larger">' + title + '</span>')
        dialog.set_title(_('Authentication required'))
        dialog.format_secondary_markup(message)
        dialog.set_default_response(gtk.RESPONSE_OK)

        if register_callback is not None:
            dialog.add_button(_('New user'), gtk.RESPONSE_HELP)

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
        dialog.destroy()

        return response == gtk.RESPONSE_OK, ( username_entry.get_text(), password_entry.get_text() )

    def show_copy_dialog(self, src_filename, dst_filename=None, dst_directory=None, title=_('Select destination')):
        if dst_filename is None:
            dst_filename = src_filename

        if dst_directory is None:
            dst_directory = os.path.expanduser('~')

        base, extension = os.path.splitext(src_filename)

        if not dst_filename.endswith(extension):
            dst_filename += extension

        if gpodder.interface == gpodder.GUI:
            dlg = gtk.FileChooserDialog(title=title, parent=self.main_window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        elif gpodder.interface == gpodder.MAEMO:
            import hildon
            dlg = hildon.FileChooserDialog(self.main_window, gtk.FILE_CHOOSER_ACTION_SAVE)

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

