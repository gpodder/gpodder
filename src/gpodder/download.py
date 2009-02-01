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
#  download.py -- Download client using DownloadStatusManager
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#

from gpodder.liblogger import log
from gpodder.libgpodder import gl
from gpodder import util
from gpodder import services
from gpodder import resolver
import gpodder

import threading
import urllib
import shutil
import os.path
import os
import time

from xml.sax import saxutils

class DownloadCancelledException(Exception): pass

class gPodderDownloadHTTPError(Exception):
    def __init__(self, url, error_code, error_message):
        self.url = url
        self.error_code = error_code
        self.error_message = error_message

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

    def http_error_default(self, url, fp, errcode, errmsg, headers):
        """
        FancyURLopener by default does not raise an exception when
        there is some unknown HTTP error code. We want to override
        this and provide a function to log the error and raise an
        exception, so we don't download the HTTP error page here.
        """
        # The following two lines are copied from urllib.URLopener's
        # implementation of http_error_default
        void = fp.read()
        fp.close()
        raise gPodderDownloadHTTPError(url, errcode, errmsg)

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

        # Make an educated guess about the total file size
        self.total_size = self.episode.length

        self.cancelled = False
        self.start_time = 0.0
        self.speed = _('Queued')
        self.speed_value = 0
        self.progress = 0.0
        self.downloader = DownloadURLOpener( self.channel)
        self.last_update = 0.0

        # Keep a copy of these global variables for comparison later        
        self.limit_rate_value = gl.config.limit_rate_value
        self.limit_rate = gl.config.limit_rate
        self.start_blocks = 0

    def cancel( self):
        self.cancelled = True

    def status_updated( self, count, blockSize, totalSize):
        if totalSize:
            # We see a different "total size" while downloading,
            # so correct the total size variable in the thread
            if totalSize != self.total_size and totalSize > 0:
                log('Correcting file size for %s from %d to %d while downloading.', self.url, self.total_size, totalSize, sender=self)
                self.total_size = totalSize
            elif totalSize < 0:
                # The current download has a negative value, so assume
                # the total size given from the feed is correct
                totalSize = self.total_size
            self.progress = 100.0*float(count*blockSize)/float(totalSize)
        else:
            self.progress = 100.0

        # Sanity checks for "progress" in valid range (0..100)
        if self.progress < 0.0:
            log('Warning: Progress is lower than 0 (count=%d, blockSize=%d, totalSize=%d)', count, blockSize, totalSize, sender=self)
            self.progress = 0.0
        elif self.progress > 100.0:
            log('Warning: Progress is more than 100 (count=%d, blockSize=%d, totalSize=%d)', count, blockSize, totalSize, sender=self)
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
                
                # Has rate limiting been enabled or disabled?                
                if self.limit_rate != gl.config.limit_rate: 
                    # If it has been enabled then reset base time and block count                    
                    if gl.config.limit_rate:
                        self.start_time = now
                        self.start_blocks = count
                    self.limit_rate = gl.config.limit_rate
                    
                # Has the rate been changed and are we currently limiting?            
                if self.limit_rate_value != gl.config.limit_rate_value and self.limit_rate: 
                    self.start_time = now
                    self.start_blocks = count
                    self.limit_rate_value = gl.config.limit_rate_value

                passed = now - self.start_time
                if passed > 0:
                    speed = ((count-self.start_blocks)*blockSize)/passed
                else:
                    speed = 0
            else:
                self.start_time = now
                self.start_blocks = count
                passed = now - self.start_time
                speed = count*blockSize

            self.speed = '%s/s' % gl.format_filesize(speed)
            self.speed_value = speed

            if gl.config.limit_rate and speed > gl.config.limit_rate_value:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                should_have_passed = float((count-self.start_blocks)*blockSize)/(gl.config.limit_rate_value*1024.0)
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
                (unused, headers) = self.downloader.retrieve( resolver.get_real_download_url(self.url), self.tempname, reporthook = self.status_updated)

                if 'content-type' in headers and headers['content-type'] != self.episode.mimetype:
                    log('Correcting mime type: %s => %s', self.episode.mimetype, headers['content-type'])
                    self.episode.mimetype = headers['content-type']
                    # File names are constructed with regard to the mime type.
                    self.filename = self.episode.local_filename()

                shutil.move( self.tempname, self.filename)
                # Get the _real_ filesize once we actually have the file
                self.episode.length = os.path.getsize(self.filename)
                self.channel.addDownloadedItem( self.episode)
                services.download_status_manager.download_completed(self.download_id)
                
                # If a user command has been defined, execute the command setting some environment variables
                if len(gl.config.cmd_download_complete) > 0:
                    os.environ["GPODDER_EPISODE_URL"]=self.episode.url or ''
                    os.environ["GPODDER_EPISODE_TITLE"]=self.episode.title or ''
                    os.environ["GPODDER_EPISODE_FILENAME"]=self.filename or ''
                    os.environ["GPODDER_EPISODE_PUBDATE"]=str(int(self.episode.pubDate))
                    os.environ["GPODDER_EPISODE_LINK"]=self.episode.link or ''
                    os.environ["GPODDER_EPISODE_DESC"]=self.episode.description or ''
                    threading.Thread(target=gl.ext_command_thread, args=(self.notification,gl.config.cmd_download_complete)).start()

            finally:
                services.download_status_manager.remove_download_id( self.download_id)
                services.download_status_manager.s_release( acquired)
        except DownloadCancelledException:
            log('Download has been cancelled: %s', self.episode.title, traceback=None, sender=self)
        except IOError, ioe:
            if self.notification is not None:
                title = ioe.strerror
                message = _('An error happened while trying to download <b>%s</b>.') % ( saxutils.escape( self.episode.title), )
                self.notification( message, title)
            log( 'Error "%s" while downloading "%s": %s', ioe.strerror, self.episode.title, ioe.filename, sender = self)
        except gPodderDownloadHTTPError, gdhe:
            if self.notification is not None:
                title = gdhe.error_message
                message = _('An error (HTTP %d) happened while trying to download <b>%s</b>.') % ( gdhe.error_code, saxutils.escape( self.episode.title), )
                self.notification( message, title)
            log( 'HTTP error %s while downloading "%s": %s', gdhe.error_code, self.episode.title, gdhe.error_message, sender=self)
        except:
            log( 'Error while downloading "%s".', self.episode.title, sender = self, traceback = True)

