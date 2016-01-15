# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import coverart

import gtk


class CoverDownloader(ObservableService):
    """
    This class manages downloading cover art and notification
    of other parts of the system. Downloading cover art can
    happen either synchronously via get_cover() or in
    asynchronous mode via request_cover(). When in async mode,
    the cover downloader will send the cover via the
    'cover-available' message (via the ObservableService).
    """

    def __init__(self):
        self.downloader = coverart.CoverDownloader()
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
        logger.debug('cover download request for %s', channel.url)
        util.run_in_background(lambda: self.__get_cover(channel,
            custom_url, True, avoid_downloading))

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

    def replace_cover(self, channel, custom_url=None):
        """
        This is a convenience function that deletes
        the current cover file and requests a new
        cover from the URL specified.
        """
        self.request_cover(channel, custom_url)

    def __get_cover(self, channel, url, async=False, avoid_downloading=False):
        def get_filename():
            return self.downloader.get_cover(channel.cover_file,
                    url or channel.cover_url, channel.url, channel.title,
                    channel.auth_username, channel.auth_password,
                    not avoid_downloading)

        if url is not None:
            filename = get_filename()
            if filename.startswith(channel.cover_file):
                logger.info('Replacing cover: %s', filename)
                util.delete_file(filename)

        filename = get_filename()
        pixbuf = None

        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        except Exception, e:
            logger.warn('Cannot load cover art', exc_info=True)
            if filename.startswith(channel.cover_file):
                logger.info('Deleting broken cover: %s', filename)
                util.delete_file(filename)
                filename = get_filename()
                pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        if async:
            self.notify('cover-available', channel, pixbuf)
        else:
            return (channel.url, pixbuf)

