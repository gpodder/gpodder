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

# Python implementation of HeAboutDialog from hildon-extras
# Copyright (c) 2010-04-11 Thomas Perl <thp@thpinfo.com>

import hildon
import gtk
import dbus

import gpodder

_ = gpodder.gettext

class HeAboutDialog(gtk.Dialog):
    RESPONSE_WEBSITE, \
    RESPONSE_BUGTRACKER, \
    RESPONSE_DONATE = range(3)

    def __init__(self):
        gtk.Dialog.__init__(self)

        self.website_url = None
        self.bugtracker_url = None
        self.donate_url = None

        self.set_title(_('About'))

        self.image_icon = gtk.Image()
        self.label_app_name = gtk.Label(app_name)
        self.label_version = gtk.Label()
        self.label_description = gtk.Label()
        self.label_copyright = gtk.Label()
        self.table_layout = gtk.Table(3, 3, False)

        hildon.hildon_helper_set_logical_font(self.label_app_name, 'X-LargeSystemFont')
        hildon.hildon_helper_set_logical_font(self.label_version, 'LargeSystemFont')
        hildon.hildon_helper_set_logical_font(self.label_copyright, 'SmallSystemFont')
        hildon.hildon_helper_set_logical_color(self.label_copyright, gtk.RC_FG, gtk.STATE_NORMAL, 'SecondaryTextColor')

        self.label_app_name.set_alignment(0, 1)
        self.label_version.set_alignment(0, 1)
        self.label_description.set_alignment(0, 0)
        self.label_copyright.set_alignment(0, 1)
        self.label_version.set_padding(10, 0)
        self.label_copyright.set_padding(0, 5)
        self.image_icon.set_padding(5, 5)

        #content_area = self.get_content_area() # Starting with PyGTK 2.14
        content_area = self.vbox

        self.table_layout.attach(self.image_icon, 0, 1, 0, 2, 0, gtk.EXPAND, 0, 0)
        self.table_layout.attach(self.label_app_name, 1, 2, 0, 1, 0, gtk.EXPAND | gtk.FILL, 0, 0)
        self.table_layout.attach(self.label_version, 2, 3, 0, 1, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL, 0, 0)
        self.table_layout.attach(self.label_description, 1, 3, 1, 2, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL, 0, 0)
        self.table_layout.attach(self.label_copyright, 0, 3, 2, 3, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL, 0, 0)
        content_area.add(self.table_layout)
        self.connect('response', self._on_response)
        self.show_all()

    def _on_response(self, dialog, response_id):
        if response_id == HeAboutDialog.RESPONSE_WEBSITE:
            self.open_webbrowser(self.website_url)
        elif response_id == HeAboutDialog.RESPONSE_BUGTRACKER:
            self.open_webbrowser(self.bugtracker_url)
        elif response_id == HeAboutDialog.RESPONSE_DONATE:
            self.open_webbrowser(self.donate_url)

    def set_app_name(self, app_name):
        self.label_app_name.set_text(app_name)
        self.set_title(_('About %s') % app_name)

    def set_icon_name(self, icon_name):
        self.image_icon.set_from_icon_name(icon_name, gtk.ICON_SIZE_DIALOG)

    def set_version(self, version):
        self.label_version.set_text(version)

    def set_description(self, description):
        self.label_description.set_text(description)

    def set_copyright(self, copyright):
        self.label_copyright.set_text(copyright)

    def set_website(self, url):
        if self.website_url is None:
            self.add_button(_('Visit website'), HeAboutDialog.RESPONSE_WEBSITE)
        self.website_url = url

    def set_bugtracker(self, url):
        if self.bugtracker_url is None:
            self.add_button(_('Report bug'), HeAboutDialog.RESPONSE_BUGTRACKER)
        self.bugtracker_url = url

    def set_donate_url(self, url):
        if self.donate_url is None:
            self.add_button(_('Donate'), HeAboutDialog.RESPONSE_DONATE)
        self.donate_url = url

    def open_webbrowser(self, url):
        bus = dbus.SessionBus()
        proxy = bus.get_object('com.nokia.osso_browser', '/com/nokia/osso_browser/request', 'com.nokia.osso_browser')
        proxy.load_url(url, dbus_interface='com.nokia.osso_browser')

    @classmethod
    def present(cls, parent=None, app_name=None, icon_name=None, \
            version=None, description=None, copyright=None, \
            website_url=None, bugtracker_url=None, donate_url=None):
        ad = cls()

        if parent is not None:
            ad.set_transient_for(parent)
            ad.set_destroy_with_parent(True)

        if app_name is not None:
            ad.set_app_name(app_name)

        ad.set_icon_name(icon_name)
        ad.set_version(version)
        ad.set_description(description)
        ad.set_copyright(copyright)

        if website_url is not None:
            ad.set_website(website_url)

        if bugtracker_url is not None:
            ad.set_bugtracker(bugtracker_url)

        if donate_url is not None:
            ad.set_donate_url(donate_url)

        ad.run()
        ad.destroy()

