# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
#  gpodder.gtkui.services - UI parts for the services module (2009-08-24)
#


import gpodder
_ = gpodder.gettext

from gpodder.services import ObservableService
from gpodder.liblogger import log

from gpodder import util
from gpodder import youtube

import gtk
import os
import urlparse
import threading

class DependencyModel(gtk.ListStore):
    C_NAME, C_DESCRIPTION, C_AVAILABLE_TEXT, C_AVAILABLE, C_MISSING = range(5)

    def __init__(self, depman):
        gtk.ListStore.__init__(self, str, str, str, bool, str)

        for feature_name, description, modules, tools in depman.dependencies:
            modules_available, module_info = depman.modules_available(modules)
            tools_available, tool_info = depman.tools_available(tools)

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

            self.append((feature_name, description, available_str, available, missing_str))


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
    MAX_SIZE = 360

    def __init__(self):
        signal_names = ['cover-available', 'cover-removed']
        ObservableService.__init__(self, signal_names)

    def request_cover(self, channel, custom_url=None, avoid_downloading=False):
        """
        Sends an asynchronous request to download a
        cover for the specific channel.

        After the cover has been downloaded, the
        "cover-available" signal will be sent with
        the channel url and new cover as pixbuf.

        If you specify a custom_url, the cover will
        be downloaded from the specified URL and not
        taken from the channel metadata.

        The optional parameter "avoid_downloading",
        when true, will make sure we return only
        already-downloaded covers and return None
        when we have no cover on the local disk.
        """
        log('cover download request for %s', channel.url, sender=self)
        args = [channel, custom_url, True, avoid_downloading]
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

    def reload_cover_from_disk(self, channel):
        self.notify('cover-removed', channel.url)
        self.request_cover(channel, None, True)

    def get_default_cover(self, channel):
        # "randomly" choose a cover based on the podcast title
        basename = 'podcast-%d.png' % (hash(channel.title)%5)
        filename = os.path.join(gpodder.images_folder, basename)
        return gtk.gdk.pixbuf_new_from_file(filename)

    def __get_cover(self, channel, url, async=False, avoid_downloading=False):
        if not async and avoid_downloading and not os.path.exists(channel.cover_file):
            return (channel.url, self.get_default_cover(channel))

        if not os.path.exists(channel.cover_file):
            if url is None:
                url = channel.image

            new_url = youtube.get_real_cover(channel.url)
            if new_url is not None:
                url = new_url

            if url is not None:
                image_data = None
                try:
                    log('Trying to download: %s', url, sender=self)

                    image_data = util.urlopen(url).read()
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

        pixbuf = None
        if os.path.exists(channel.cover_file):
            try:
                pixbuf = gtk.gdk.pixbuf_new_from_file(channel.cover_file.decode(util.encoding, 'ignore'))
            except:
                log('Data error while loading %s', channel.cover_file, sender=self)

        if pixbuf is None:
            pixbuf = self.get_default_cover(channel)

        # Resize if width is too large
        if pixbuf.get_width() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        # Resize if height is too large
        if pixbuf.get_height() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        if async:
            self.notify('cover-available', channel, pixbuf)
        else:
            return (channel.url, pixbuf)

