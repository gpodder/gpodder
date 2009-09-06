#!/usr/bin/python

import glob
import gtk
import re
import xml.dom.minidom

def xml_text_contents(node):
    return ''.join(n.data for n in node.childNodes if n.nodeType==n.TEXT_NODE)

# Set of icon file names
icon_names = set()

# GtkBuilder .ui files for the interface
ui_files = glob.glob('data/ui/*.ui') + \
           glob.glob('data/ui/maemo/*.ui')

# Python source files
py_files = glob.glob('src/gpodder/*.py') + \
           glob.glob('src/gpodder/gtkui/*.py') + \
           glob.glob('src/gpodder/gtkui/interface/*.py') + \
           glob.glob('src/gpodder/gtkui/maemo/*.py')



for ui_file in ui_files:
    doc = xml.dom.minidom.parse(ui_file)

    for node in doc.getElementsByTagName('property'):
        name = node.getAttribute('name').replace('_', '-')
        value = xml_text_contents(node)
        if (name in ('icon-name', 'stock-id', 'stock')) or \
           (name == 'label' and value.startswith('gtk-')):
            icon_names.add(value)

for py_file in py_files:
    data = open(py_file, 'r').read()
    for match in re.finditer(r'gtk\.(STOCK_[_A-Z]+)', data):
        stock_id = getattr(gtk, match.group(1), None)
        if stock_id is not None:
            icon_names.add(stock_id)

    # Match ICON('iconname') and ICON("iconname")
    for match in re.finditer(r'ICON\(["\']([^"\']*)["\']\)', data):
        icon_names.add(match.group(1))



for icon_name in sorted(icon_names):
    print icon_name


