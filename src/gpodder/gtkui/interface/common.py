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

import gtk
import os
import shutil
import sys

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.base import GtkBuilderWidget

from gpodder.gtkui.widgets import NotificationWindow

# For gPodder on Fremantle
class Orientation(object):
    LANDSCAPE, PORTRAIT = range(2)

try:
    import pynotify
    if not pynotify.init('gPodder'):
        pynotify = None
except ImportError:
    pynotify = None

class BuilderWidget(GtkBuilderWidget):
    finger_friendly_widgets = []

    def __init__(self, parent, **kwargs):
        self._window_iconified = False
        self._window_visible = False

        # Enable support for portrait mode changes on Maemo 5
        if gpodder.ui.fremantle:
            self._window_orientation = Orientation.LANDSCAPE

        GtkBuilderWidget.__init__(self, gpodder.ui_folders, gpodder.textdomain, **kwargs)

        # Enable support for portrait mode changes on Maemo 5
        if gpodder.ui.fremantle:
            self.main_window.connect('configure-event', \
                    self._on_configure_event_maemo)

        # Enable support for fullscreen toggle key on Maemo 4
        if gpodder.ui.diablo:
            self._maemo_fullscreen = False
            self._maemo_fullscreen_chain = None
            self.main_window.connect('key-press-event', \
                    self._on_key_press_event_maemo)
            self.main_window.connect('window-state-event', \
                    self._on_window_state_event_maemo)

        # Enable support for tracking iconified state
        if hasattr(self, 'on_iconify') and hasattr(self, 'on_uniconify'):
            self.main_window.connect('window-state-event', \
                    self._on_window_state_event_iconified)

        # Enable support for tracking visibility state
        if gpodder.ui.desktop:
            self.main_window.connect('visibility-notify-event', \
                        self._on_window_state_event_visibility)

        # Set widgets to finger-friendly mode if on Maemo
        for widget_name in self.finger_friendly_widgets:
            if hasattr(self, widget_name):
                self.set_finger_friendly(getattr(self, widget_name))

        if parent is not None:
            self.main_window.set_transient_for(parent)

            if gpodder.ui.desktop:
                if hasattr(self, 'center_on_widget'):
                    (x, y) = parent.get_position()
                    a = self.center_on_widget.allocation
                    (x, y) = (x + a.x, y + a.y)
                    (w, h) = (a.width, a.height)
                    (pw, ph) = self.main_window.get_size()
                    self.main_window.move(x + w/2 - pw/2, y + h/2 - ph/2)
            elif gpodder.ui.diablo:
                self._maemo_fullscreen_chain = parent
                if parent.window.get_state() & gtk.gdk.WINDOW_STATE_FULLSCREEN:
                    self.main_window.fullscreen()
                    self._maemo_fullscreen = True

    def on_window_orientation_changed(self, orientation):
        """Override this method to relayout a window for portrait mode."""
        pass

    def _on_configure_event_maemo(self, window, event):
        if float(event.width)/float(event.height) < 1:
            orientation = Orientation.PORTRAIT
        else:
            orientation = Orientation.LANDSCAPE

        if orientation != self._window_orientation:
            self.on_window_orientation_changed(orientation)
            self._window_orientation = orientation

    def _on_key_press_event_maemo(self, widget, event):
        window_type = widget.get_type_hint()
        if window_type != gtk.gdk.WINDOW_TYPE_HINT_NORMAL:
            return False

        if event.keyval == gtk.keysyms.F6:
            if self._maemo_fullscreen:
                if self._maemo_fullscreen_chain is not None:
                    self._maemo_fullscreen_chain.unfullscreen()
                self.main_window.unfullscreen()
                if not self.use_fingerscroll:
                    self.main_window.set_border_width(0)
            else:
                if self._maemo_fullscreen_chain is not None:
                    self._maemo_fullscreen_chain.fullscreen()
                self.main_window.fullscreen()
                if not self.use_fingerscroll:
                    self.main_window.set_border_width(12)
            return True
        else:
            return False

    def _on_window_state_event_maemo(self, widget, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self._maemo_fullscreen = True
        else:
            self._maemo_fullscreen = False

        return False

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
        """Return a gtk.Window that should be the parent of dialogs

        On non-Fremantle environments, this simply returns the main
        window of this dialog. On Fremantle, it tries to determine
        the topmost window from the window stack if possible.
        """
        if gpodder.ui.fremantle:
            # Determine the topmost visible window and attach the
            # message to that window to avoid Maemo Bug 10030
            stack = hildon.WindowStack.get_default()
            visible_windows = stack.get_windows()
            if visible_windows:
                parent_window = visible_windows[0]

        return self.main_window

    def show_message(self, message, title=None, important=False, widget=None):
        if gpodder.ui.diablo:
            import hildon
            if important:
                try:
                    dlg = hildon.Note('information', (self.main_window, message))
                except TypeError:
                    if title is None:
                        message = message
                    else:
                        message = '%s\n%s' % (title, message)
                    dlg = hildon.hildon_note_new_information(self.main_window, \
                            message)
                dlg.run()
                dlg.destroy()
            else:
                if title is None:
                    title = 'gPodder'
                pango_markup = '<b>%s</b>\n<small>%s</small>' % (title, message)
                try:
                    hildon.hildon_banner_show_information_with_markup(gtk.Label(''), None, pango_markup)
                except TypeError:
                    # We're probably running the Diablo UI on Maemo 5 :)
                    hildon.hildon_banner_show_information(self.main_window, \
                            '', message)
        elif gpodder.ui.fremantle:
            import hildon
            if important:
                if title is None:
                    message = message
                else:
                    message = '%s\n%s' % (title, message)

                dlg = hildon.hildon_note_new_information( \
                        self.get_dialog_parent(), \
                        message)
                dlg.run()
                dlg.destroy()
            else:
                hildon.hildon_banner_show_information(self.main_window, \
                        '', message)
        else:
            # XXX: Dirty hack to get access to the gPodder-specific config object
            config = getattr(self, '_config', getattr(self, 'config', None))

            if important:
                dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
                if title:
                    dlg.set_title(str(title))
                    dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
                else:
                    dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
                dlg.run()
                dlg.destroy()
            elif config is not None and config.enable_notifications:
                if pynotify is not None:
                    if title is None:
                        title = 'gPodder'
                    notification = pynotify.Notification(title, message,\
                            gpodder.icon_file)
                    try:
                        notification.show()
                    except:
                        # See http://gpodder.org/bug/966
                        pass
                elif widget and isinstance(widget, gtk.Widget):
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

        if gpodder.ui.diablo or gpodder.ui.fremantle:
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
        if gpodder.ui.desktop:
            dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
            if title:
                dlg.set_title(str(title))
                dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
            else:
                dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
            response = dlg.run()
            dlg.destroy()
            return response == gtk.RESPONSE_YES
        elif gpodder.ui.diablo:
            import hildon
            try:
                dlg = hildon.Note('confirmation', (self.main_window, message))
            except TypeError:
                # Kludgy workaround: We're running the Diablo UI on Maemo 5 :)
                dlg = hildon.hildon_note_new_confirmation(self.main_window, \
                        message)
            response = dlg.run()
            dlg.destroy()
            return response == gtk.RESPONSE_OK
        elif gpodder.ui.fremantle:
            import hildon
            dlg = hildon.hildon_note_new_confirmation(self.get_dialog_parent(), \
                    message)
            response = dlg.run()
            dlg.destroy()
            return response == gtk.RESPONSE_OK
        else:
            raise Exception('Unknown interface type')

    def show_text_edit_dialog(self, title, prompt, text=None, empty=False, \
            is_url=False):
        dialog = gtk.Dialog(title, self.get_dialog_parent(), \
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        
        if gpodder.ui.fremantle:
            import hildon
            button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | \
                    gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_text(_('OK'), '')
            dialog.add_action_widget(button, gtk.RESPONSE_OK)
        else:
            cancel_button = dialog.add_button(gtk.STOCK_CANCEL, \
                    gtk.RESPONSE_CANCEL)
            ok_button = dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)

        dialog.set_has_separator(False)
        if gpodder.ui.desktop:
            dialog.set_default_size(300, -1)
        else:
            dialog.set_default_size(650, -1)
        dialog.set_default_response(gtk.RESPONSE_OK)

        if gpodder.ui.fremantle:
            import hildon
            text_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
            if is_url:
                # Disable word capitalization and word completion when
                # requesting an URL to be entered (see Maemo bug 5184)
                text_entry.set_property('hildon-input-mode', \
                        gtk.HILDON_GTK_INPUT_MODE_FULL)
        elif gpodder.ui.diablo:
            import hildon
            text_entry = gtk.Entry()
            text_entry.set_property('hildon-input-mode', \
                    'HILDON_GTK_INPUT_MODE_FULL')
        else:
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
        if not gpodder.ui.fremantle:
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

    def show_login_dialog(self, title, message, username=None, password=None, username_prompt=_('Username'), register_callback=None):
        """ An authentication dialog based on
                http://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/ """

        if gpodder.ui.fremantle:
            dialog = gtk.Dialog(title, self.main_window,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    (str(_('Login')), gtk.RESPONSE_OK))
            dialog.vbox.add(gtk.Label(message))
        else:
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
            dialog.add_button(_('New user'), gtk.RESPONSE_HELP)

        if gpodder.ui.fremantle:
            import hildon
            username_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
            password_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        else:
            username_entry = gtk.Entry()
            password_entry = gtk.Entry()

        if gpodder.ui.maemo:
            # Disable input capitalization for the login fields
            username_entry.set_property('hildon-input-mode', \
                        gtk.HILDON_GTK_INPUT_MODE_FULL)
            password_entry.set_property('hildon-input-mode', \
                        gtk.HILDON_GTK_INPUT_MODE_FULL)

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

        if gpodder.ui.desktop or gpodder.ui.fremantle:
            # FIXME: Hildonization for Fremantle
            dlg = gtk.FileChooserDialog(title=title, parent=self.main_window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        elif gpodder.ui.diablo:
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

class TreeViewHelper(object):
    """Container for gPodder-specific TreeView attributes."""
    BUTTON_PRESS = '_gpodder_button_press'
    LAST_TOOLTIP = '_gpodder_last_tooltip'
    CAN_TOOLTIP = '_gpodder_can_tooltip'
    ROLE = '_gpodder_role'

    # Enum for the role attribute
    ROLE_PODCASTS, ROLE_EPISODES, ROLE_DOWNLOADS = range(3)

    @classmethod
    def set(cls, treeview, role):
        setattr(treeview, cls.BUTTON_PRESS, (0, 0))
        setattr(treeview, cls.LAST_TOOLTIP, None)
        setattr(treeview, cls.CAN_TOOLTIP, True)
        setattr(treeview, cls.ROLE, role)

    @classmethod
    def save_button_press_event(cls, treeview, event):
        setattr(treeview, cls.BUTTON_PRESS, (event.x, event.y))
        return True

    @classmethod
    def get_button_press_event(cls, treeview):
        return getattr(treeview, cls.BUTTON_PRESS)

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

