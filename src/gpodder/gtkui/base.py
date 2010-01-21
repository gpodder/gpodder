# -*- coding: utf-8 -*-
"""
UI Base Module for GtkBuilder

Based on SimpleGladeApp.py Copyright (C) 2004 Sandino Flores Moreno
"""

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import sys
import re

import tokenize

import gtk

class GtkBuilderWidget(object):
    # Other code can set this to True if it wants us to try and
    # replace GtkScrolledWindow widgets with Finger Scroll widgets
    use_fingerscroll = False

    def __init__(self, ui_folders, textdomain, **kwargs):
        """
        Loads the UI file from the specified folder (with translations
        from the textdomain) and initializes attributes.

        ui_folders:
            List of folders with GtkBuilder .ui files in search order

        textdomain:
            The textdomain to be used for translating strings

        **kwargs:
            Keyword arguments will be set as attributes to this window
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.builder = gtk.Builder()
        self.builder.set_translation_domain(textdomain)

        print >>sys.stderr, 'Creating new from file', self.__class__.__name__

        ui_file = '%s.ui' % self.__class__.__name__.lower()

        # Search for the UI file in the UI folders, stop after first match
        for ui_folder in ui_folders:
            filename = os.path.join(ui_folder, ui_file)
            if os.path.exists(filename):
                self.builder.add_from_file(filename)
                break

        self.builder.connect_signals(self)
        self.set_attributes()

        self.new()

    def _handle_scrolledwindow(self, widget):
        """Helper for replacing gtk.ScrolledWindow with finger scroll

        This function tries to replace a gtk.ScrolledWindow
        widget with a finger scroll widget if available, reparenting
        the child widget and trying to place the finger scroll
        widget exactly where the ScrolledWindow was.

        This function needs use_fingerscroll to be set to True,
        otherwise it won't do anything."""
        if not self.use_fingerscroll:
            return widget

        # Check if we have mokoui OR hildon before continuing
        mokoui, hildon = None, None
        try:
            import mokoui
        except ImportError, ie:
            try:
                import hildon
            except ImportError, ie:
                return widget
            if not hasattr(hildon, 'PannableArea'):
                # Probably using an older version of Hildon
                return widget

        parent = widget.get_parent()
        child = widget.get_child()
        scroll = None

        def create_fingerscroll():
            if mokoui is not None:
                scroll = mokoui.FingerScroll()
                scroll.set_property('mode', 0)
                scroll.set_property('spring-speed', 0)
                scroll.set_property('deceleration', .975)
            else:
                scroll = hildon.PannableArea()

            # The following call looks ugly, but see Gnome bug 591085
            scroll.set_name(gtk.Buildable.get_name(widget))

            return scroll

        def container_get_child_pos(container, widget):
            for pos, child in enumerate(container.get_children()):
                if child == widget:
                    return pos
            return -1

        if isinstance(parent, gtk.Paned):
            scroll = create_fingerscroll()
            child.reparent(scroll)

            if parent.get_child1() == widget:
                add_to_paned = parent.add1
            else:
                add_to_paned = parent.add2

            parent.remove(widget)
            add_to_paned(scroll)
        elif isinstance(parent, gtk.Box):
            scroll = create_fingerscroll()
            child.reparent(scroll)

            position = container_get_child_pos(parent, widget)
            packing = parent.query_child_packing(widget)

            parent.remove(widget)
            parent.add(scroll)
            parent.set_child_packing(scroll, *packing)
            parent.reorder_child(scroll, position)
        elif isinstance(parent, gtk.Table):
            scroll = create_fingerscroll()
            child.reparent(scroll)

            attachment = parent.child_get(widget, 'left-attach', \
                    'right-attach', 'top-attach', 'bottom-attach', \
                    'x-options', 'y-options', 'x-padding', 'y-padding')
            parent.remove(widget)
            parent.attach(scroll, *attachment)

        if scroll is not None:
            if isinstance(child, gtk.TextView):
                child.set_editable(False)
                child.set_cursor_visible(False)
                child.set_sensitive(False)
            widget.destroy()
            scroll.show()
            return scroll

        return widget

    def set_attributes(self):
        """
        Convert widget names to attributes of this object.

        It means a widget named vbox-dialog in GtkBuilder
        is refered using self.vbox_dialog in the code.
        """
        for widget in self.builder.get_objects():
            if not hasattr(widget, 'get_name'):
                continue

            if isinstance(widget, gtk.ScrolledWindow):
                widget = self._handle_scrolledwindow(widget)

            # The following call looks ugly, but see Gnome bug 591085
            widget_name = gtk.Buildable.get_name(widget)

            widget_api_name = '_'.join(re.findall(tokenize.Name, widget_name))
            widget.set_name(widget_api_name)
            if hasattr(self, widget_api_name):
                raise AttributeError("instance %s already has an attribute %s" % (self,widget_api_name))
            else:
                setattr(self, widget_api_name, widget)
    
    @property
    def main_window(self):
        """Returns the main window of this GtkBuilderWidget"""
        return getattr(self, self.__class__.__name__)

    def new(self):
        """
        Method called when the user interface is loaded and ready to be used.
        At this moment, the widgets are loaded and can be refered as self.widget_name
        """
        pass

    def main(self):
        """
        Starts the main loop of processing events.
        The default implementation calls gtk.main()

        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main()

        Do not directly call this method in your programs.
        Use the method run() instead.
        """
        gtk.main()

    def quit(self):
        """
        Quit processing events.
        The default implementation calls gtk.main_quit()
        
        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main_quit()
        """
        gtk.main_quit()

    def run(self):
        """
        Starts the main loop of processing events checking for Control-C.

        The default implementation checks wheter a Control-C is pressed,
        then calls on_keyboard_interrupt().

        Use this method for starting programs.
        """
        try:
            self.main()
        except KeyboardInterrupt:
            self.on_keyboard_interrupt()

    def on_keyboard_interrupt(self):
        """
        This method is called by the default implementation of run()
        after a program is finished by pressing Control-C.
        """
        pass

