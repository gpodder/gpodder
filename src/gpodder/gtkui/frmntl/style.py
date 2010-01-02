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
import hildon

# See the Fremantle Master Layout Guide for more information:
# http://tinyurl.com/fremantle-master-layout-guide

# For implementation details, consult hildon/hildon-helper.c
# (the function is called hildon_change_style_recursive_from_list)

logical_font_names = (
        'SystemFont',
        'EmpSystemFont',
        'SmallSystemFont', # Used for secondary text in buttons/TreeViews
        'EmpSmallSystemFont',
        'LargeSystemFont', # Used for empty TreeView text
        'X-LargeSystemFont',
        'XX-LargeSystemFont',
        'XXX-LargeSystemFont',
        'HomeSystemFont',
)

logical_color_names = (
        'ButtonTextColor',
        'ButtonTextPressedColor',
        'ButtonTextDisabledColor',
        'ActiveTextColor', # Used for Button values, etc..
        'SecondaryTextColor', # Used for additional/secondary information
)

def get_font_desc(logicalfontname):
    settings = gtk.settings_get_default()
    font_style = gtk.rc_get_style_by_paths(settings, logicalfontname, \
            None, None)
    font_desc = font_style.font_desc
    return font_desc

def get_color(logicalcolorname):
    settings = gtk.settings_get_default()
    color_style = gtk.rc_get_style_by_paths(settings, 'GtkButton', \
            'osso-logical-colors', gtk.Button)
    return color_style.lookup_color(logicalcolorname)


# For debugging; usage: python -m gpodder.gtkui.frmntl.style
if __name__ == '__main__':
    for font_name in logical_font_names:
        print font_name, '-> ', get_font_desc(font_name).to_string()
    print '-----------'
    for color_name in logical_color_names:
        print color_name, '-> ', get_color(color_name).to_string()

