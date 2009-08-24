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


#
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-08-24
#
#

from __future__ import with_statement

import gpodder
from gpodder.liblogger import log

from gpodder import util
from gpodder import resolver
from gpodder import download

import gtk
import gobject

import threading
import time
import urllib2
import os

_ = gpodder.gettext

class ObservableService(object):
    def __init__(self, signal_names=[]):
        self.observers = {}
        for signal in signal_names:
            self.observers[signal] = []

    def register(self, signal_name, observer):
        if signal_name in self.observers:
            if not observer in self.observers[signal_name]:
                self.observers[signal_name].append(observer)
            else:
                log('Observer already added to signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for registration.', signal_name, sender=self)

    def unregister(self, signal_name, observer):
        if signal_name in self.observers:
            if observer in self.observers[signal_name]:
                self.observers[signal_name].remove(observer)
            else:
                log('Observer could not be removed from signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for un-registration.', signal_name, sender=self)

    def notify(self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                util.idle_add(observer, *args)
        else:
            log('Signal "%s" is not available for notification.', signal_name, sender=self)


class DependencyManager(object):
    def __init__(self):
        self.dependencies = []

    def depend_on(self, feature_name, description, modules, tools):
        self.dependencies.append([feature_name, description, modules, tools])

    def modules_available(self, modules):
        """
        Receives a list of modules and checks if each
        of them is available. Returns a tuple with the
        first item being a boolean variable that is True
        when all required modules are available and False
        otherwise. The second item is a dictionary that
        lists every module as key with the available as
        boolean value.
        """
        result = {}
        all_available = True
        for module in modules:
            try:
                __import__(module)
                result[module] = True
            except:
                result[module] = False
                all_available = False

        return (all_available, result)

    def tools_available(self, tools):
        """
        See modules_available.
        """
        result = {}
        all_available = True
        for tool in tools:
            if util.find_command(tool):
                result[tool] = True
            else:
                result[tool] = False
                all_available = False

        return (all_available, result)

    def get_model(self):
        # Name, Description, Available (str), Available (bool), Missing (str)
        model = gtk.ListStore(str, str, str, bool, str)
        for feature_name, description, modules, tools in self.dependencies:
            modules_available, module_info = self.modules_available(modules)
            tools_available, tool_info = self.tools_available(tools)

            available = modules_available and tools_available
            if available:
                available_str = _('Available')
            else:
                available_str = _('Missing dependencies')

            missing_str = []
            for module in modules:
                if not module_info[module]:
                    missing_str.append(_('Python module "%s" not installed') % module)
            for tool in tools:
                if not tool_info[tool]:
                    missing_str.append(_('Command "%s" not installed') % tool)
            missing_str = '\n'.join(missing_str)

            model.append([feature_name, description, available_str, available, missing_str])
        return model


dependency_manager = DependencyManager()


# Register non-module-specific dependencies here
dependency_manager.depend_on(_('Bluetooth file transfer'), _('Send podcast episodes to Bluetooth devices. Needs Python Bluez bindings.'), ['bluetooth'], ['bluetooth-sendto'])
dependency_manager.depend_on(_('HTML episode shownotes'), _('Display episode shownotes in HTML format using GTKHTML2.'), ['gtkhtml2'], [])


class CoverDownloader(ObservableService):
    """
    This class manages downloading cover art and notification
    of other parts of the system. Downloading cover art can
    happen either synchronously via get_cover() or in
    asynchronous mode via request_cover(). When in async mode,
    the cover downloader will send the cover via the
    'cover-available' message (via the ObservableService).
    """

    # Maximum width/height of the cover in pixels
    MAX_SIZE = 400

    def __init__(self):
        signal_names = ['cover-available', 'cover-removed']
        ObservableService.__init__(self, signal_names)

    def request_cover(self, channel, custom_url=None):
        """
        Sends an asynchronous request to download a
        cover for the specific channel.

        After the cover has been downloaded, the
        "cover-available" signal will be sent with
        the channel url and new cover as pixbuf.

        If you specify a custom_url, the cover will
        be downloaded from the specified URL and not
        taken from the channel metadata.
        """
        log('cover download request for %s', channel.url, sender=self)
        args = [channel, custom_url, True]
        threading.Thread(target=self.__get_cover, args=args).start()

    def get_cover(self, channel, custom_url=None, avoid_downloading=False):
        """
        Sends a synchronous request to download a
        cover for the specified channel.

        The cover will be returned to the caller.

        The custom_url has the same semantics as
        in request_cover().

        The optional parameter "avoid_downloading",
        when true, will make sure we return only
        already-downloaded covers and return None
        when we have no cover on the local disk.
        """
        (url, pixbuf) = self.__get_cover(channel, custom_url, False, avoid_downloading)
        return pixbuf

    def remove_cover(self, channel):
        """
        Removes the current cover for the channel
        so that a new one is downloaded the next
        time we request the channel cover.
        """
        util.delete_file(channel.cover_file)
        self.notify('cover-removed', channel.url)

    def replace_cover(self, channel, custom_url=None):
        """
        This is a convenience function that deletes
        the current cover file and requests a new
        cover from the URL specified.
        """
        self.remove_cover(channel)
        self.request_cover(channel, custom_url)

    def __get_cover(self, channel, url, async=False, avoid_downloading=False):
        if not async and avoid_downloading and not os.path.exists(channel.cover_file):
            return (channel.url, None)

        loader = gtk.gdk.PixbufLoader()
        pixbuf = None

        if not os.path.exists(channel.cover_file):
            if url is None:
                url = channel.image

            new_url = resolver.get_real_cover(channel.url)
            if new_url is not None:
                url = new_url

            if url is not None:
                image_data = None
                try:
                    log('Trying to download: %s', url, sender=self)

                    image_data = urllib2.urlopen(url).read()
                except:
                    log('Cannot get image from %s', url, sender=self)
             
                if image_data is not None:
                    log('Saving image data to %s', channel.cover_file, sender=self)
                    try:
                        fp = open(channel.cover_file, 'wb')
                        fp.write(image_data)
                        fp.close()
                    except IOError, ioe:
                        log('Cannot save image due to I/O error', sender=self, traceback=True)

        if os.path.exists(channel.cover_file):
            try:
                loader.write(open(channel.cover_file, 'rb').read())
                loader.close()
                pixbuf = loader.get_pixbuf()
            except:
                log('Data error while loading %s', channel.cover_file, sender=self)
        else:
            try:
                loader.close()
            except:
                pass

#        if pixbuf is not None:
#            new_pixbuf = util.resize_pixbuf_keep_ratio(pixbuf, self.MAX_SIZE, self.MAX_SIZE)
#            if new_pixbuf is not None:
#                # Save the resized cover so we do not have to
#                # resize it next time we load it
#                new_pixbuf.save(channel.cover_file, 'png')
#                pixbuf = new_pixbuf

        if async:
            self.notify('cover-available', channel.url, pixbuf)
        else:
            return (channel.url, pixbuf)

cover_downloader = CoverDownloader()


