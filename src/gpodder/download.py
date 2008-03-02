# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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
#  download.py -- Download client using DownloadStatusManager
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#

from gpodder.liblogger import log
from gpodder.libgpodder import gl
from gpodder import util
from gpodder import services
import gpodder

import threading
import urllib
import shutil
import os.path
import time

from xml.sax import saxutils

class DownloadCancelledException(Exception): pass


class DownloadURLOpener(urllib.FancyURLopener):
    version = gpodder.user_agent

    def __init__( self, channel):
        if gl.config.proxy_use_environment:
            proxies = None
        else:
            proxies = {}
            if gl.config.http_proxy:
                proxies['http'] = gl.config.http_proxy
            if gl.config.ftp_proxy:
                proxies['ftp'] = gl.config.ftp_proxy

        self.channel = channel
        urllib.FancyURLopener.__init__( self, proxies)

    def prompt_user_passwd( self, host, realm):
        if self.channel.username or self.channel.password:
            log( 'Authenticating as "%s" to "%s" for realm "%s".', self.channel.username, host, realm, sender = self)
            return ( self.channel.username, self.channel.password )

        return ( None, None )


class DownloadThread(threading.Thread):
    MAX_UPDATES_PER_SEC = 1

    def __init__( self, channel, episode, notification = None):
        threading.Thread.__init__( self)
        self.setDaemon( True)

        self.channel = channel
        self.episode = episode

        self.notification = notification

        self.url = self.episode.url
        self.filename = self.episode.local_filename()
        self.tempname = os.path.join( os.path.dirname( self.filename), '.tmp-' + os.path.basename( self.filename))

        self.limit_rate = gl.config.limit_rate
        self.limit_rate_value = gl.config.limit_rate_value

        self.cancelled = False
        self.start_time = 0.0
        self.speed = _('Queued')
        self.progress = 0.0
        self.downloader = DownloadURLOpener( self.channel)
        self.last_update = 0.0

    def cancel( self):
        self.cancelled = True

    def status_updated( self, count, blockSize, totalSize):
        if totalSize:
            self.progress = 100.0*float(count*blockSize)/float(totalSize)
        else:
            self.progress = 100.0

        self.calculate_speed( count, blockSize)
        if self.last_update < time.time() - (1.0 / self.MAX_UPDATES_PER_SEC):
            services.download_status_manager.update_status( self.download_id, speed = self.speed, progress = self.progress)
            self.last_update = time.time()

        if self.cancelled:
            util.delete_file( self.tempname)
            raise DownloadCancelledException()

    def calculate_speed( self, count, blockSize):
        if count % 5 == 0:
            now = time.time()
            if self.start_time > 0:
                passed = now - self.start_time
                if passed > 0:
                    speed = (count*blockSize)/passed
                else:
                    speed = 0
            else:
                self.start_time = now
                passed = now - self.start_time
                speed = count*blockSize
            self.speed = '%s/s' % gl.format_filesize(speed)

            if self.limit_rate and speed > self.limit_rate_value:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                should_have_passed = float(count*blockSize)/(self.limit_rate_value*1024.0)
                if should_have_passed > passed:
                    # sleep a maximum of 10 seconds to not cause time-outs
                    delay = min( 10.0, float(should_have_passed-passed))
                    time.sleep( delay)

    def run( self):
        self.download_id = services.download_status_manager.reserve_download_id()
        services.download_status_manager.register_download_id( self.download_id, self)

        # Initial status update
        services.download_status_manager.update_status( self.download_id, episode = self.episode.title, url = self.episode.url, speed = self.speed, progress = self.progress)

        acquired = services.download_status_manager.s_acquire()
        try:
            try:
                if self.cancelled:
                    return
         
                util.delete_file( self.tempname)
                self.downloader.retrieve( self.episode.url, self.tempname, reporthook = self.status_updated)
                shutil.move( self.tempname, self.filename)
                self.channel.addDownloadedItem( self.episode)
                services.download_status_manager.download_completed(self.download_id)
            finally:
                services.download_status_manager.remove_download_id( self.download_id)
                services.download_status_manager.s_release( acquired)
        except DownloadCancelledException:
            log( 'Download has been cancelled: %s', self.episode.title, sender = self)
        except IOError, ioe:
            if self.notification != None:
                title = ioe.strerror
                message = _('An error happened while trying to download <b>%s</b>.') % ( saxutils.escape( self.episode.title), )
                self.notification( message, title)
            log( 'Error "%s" while downloading "%s": %s', ioe.strerror, self.episode.title, ioe.filename, sender = self)
        except:
            log( 'Error while downloading "%s".', self.episode.title, sender = self, traceback = True)

