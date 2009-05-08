#!/usr/bin/python
#
# gtk-builder-clean.py - Remove unnecessary properties in GtkBuilder UI files
# Thomas Perl <thpinfo.com>; 2009-05-08
#
# Tries to instanciate GObjects defined in the GtkBuilder .ui file in order to
# get their default properties and then tries to compare the values defined in
# the .ui file. If the value in the .ui file is the same as the default value,
# the property is dropped from the UI file (because it is redundant).
# 
# Usage: python gtk-builder-clean.py my.ui | xmllint --format - >my.ui.fixed
#

from xml.dom import minidom

import sys
import gtk
import gtk.gdk
import gobject
import pango

if len(sys.argv) != 2:
    print >>sys.stderr, """
    Usage: %s interfacefile.ui
    """ % sys.argv[0]
    sys.exit(1)

ui = minidom.parse(sys.argv[1])

builder = gtk.Builder()

removed_properties = 0

def get_text(nodes):
    return ''.join(n.data for n in nodes if n.nodeType == n.TEXT_NODE)

def check_default(default, value):
    try:
        if default is not None:
            value = type(default)(value)
    except TypeError, ve:
        if value.startswith('GTK_') or value.startswith('PANGO_') or value.startswith('GDK_'):
            try:
                value = eval(value.replace('GTK_', 'gtk.').replace('PANGO_', 'pango.').replace('GDK_', 'gtk.gdk.'))
            except NameError, ne:
                print >>sys.stderr, ne
            except AttributeError, at:
                print >>sys.stderr, ae
        else:
            print >>sys.stderr, ve
            return False

    #print default, '<=>', value
    return default == value

def recurse(node):
    global removed_properties
    for child in node.childNodes:
        if child.nodeType != child.ELEMENT_NODE:
            recurse(child)
            continue

        class_ = child.getAttribute('class')
        if class_:
            type_ = builder.get_type_from_name(class_)
            object = gobject.new(type_)
            for property in gobject.list_properties(type_):
                try:
                    default = object.get_property(property.name)
                except TypeError, te:
                    default = None

                for child_node in child.childNodes:
                    if getattr(child_node, 'tagName', None) == 'property' \
                        and child_node.getAttribute('name') == property.name:
                            if check_default(default, get_text(child_node.childNodes)):
                                removed_properties += 1
                                child.removeChild(child_node)
                                child_node.unlink()
        recurse(child)

recurse(ui.documentElement)

print >>sys.stderr, 'Removed %d default properties in %s' % (removed_properties, sys.argv[1])
print ui.toprettyxml('', '', 'utf-8')

