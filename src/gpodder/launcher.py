#!/usr/bin/env python
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

"""Win32 Launcher script for gPodder

This is only used for the Win32 version of gPodder
and will set up the environment to find all files
and then start up the gPodder GUI.

Thomas Perl <thpinfo.com>; 2009-05-09
"""

import sys
import os
import os.path

import gettext

if __name__ == '__main__':
    prefix = os.path.abspath(os.path.normpath('.'))
    data_dir = os.path.join(prefix, 'data')

    locale_dir = os.path.join(data_dir, 'locale')
    ui_folder = os.path.join(data_dir, 'ui')
    credits_file = os.path.join(data_dir, 'credits.txt')
    images_folder = os.path.join(data_dir, 'images')
    icon_file = os.path.join(data_dir, 'gpodder.svg')

    # Set up the path to translation files
    gettext.bindtextdomain('gpodder', locale_dir)

    import gpodder

    if not gpodder.win32:
        print >>sys.stderr, 'This launcher is only for Win32.'
        sys.exit(1)

    # Enable i18n for gPodder translations
    _ = gpodder.gettext

    # Set up paths to folder with GtkBuilder files and gpodder.svg
    gpodder.ui_folders.append(ui_folder)
    gpodder.ui_folders.append(os.path.join(ui_folder, 'desktop'))
    gpodder.icon_file = icon_file
    gpodder.credits_file = credits_file
    gpodder.images_folder = images_folder
    gpodder.ui.desktop = True

    # Portable version support
    if (os.path.exists('downloads') and os.path.exists('config')) or \
       not os.path.exists(os.path.expanduser('~/.config/gpodder')):
        home = os.path.join(os.getcwd(), 'config')
        if not os.path.exists(home):
            os.mkdir(home)
        gpodder.home = home
        gpodder.subscription_file = os.path.join(home, 'channels.opml')
        gpodder.config_file = os.path.join(home, 'gpodder.conf')
        gpodder.database_file = os.path.join(home, 'database.sqlite')
        download_dir = os.path.join(os.getcwd(), 'downloads')
        os.environ['GPODDER_DOWNLOAD_DIR'] = download_dir

    from gpodder import gui

    class options(object):
        subscribe = None

    gui.main(options)

