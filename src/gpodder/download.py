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
from gpodder.dbsqlite import db
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

# The following is based on Python's urllib.py "URLopener.retrieve"
# Also based on http://mail.python.org/pipermail/python-list/2001-October/110069.html

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        # The next line is taken from urllib's URLopener.open_http
        # method, at the end after the line "if errcode == 200:"
        return urllib.addinfourl(fp, headers, 'http:' + url)

    def retrieve_resume(self, url, filename, reporthook=None, data=None):
        """retrieve_resume(url) returns (filename, headers) for a local object
        or (tempfilename, headers) for a remote object.

        The filename argument is REQUIRED (no tempfile creation code here!)

        Additionally resumes a download if the local filename exists"""

        current_size = 0
        tfp = None
        if os.path.exists(filename):
            try:
                current_size = os.path.getsize(filename)
                tfp = open(filename, 'ab')
                #If the file exists, then only download the remainder
                self.addheader('Range', 'bytes=%s-' % (current_size))
            except:
                log('Cannot open file for resuming: %s', filename, sender=self, traceback=True)
                tfp = None
                current_size = 0

        if tfp is None:
            tfp = open(filename, 'wb')

        url = urllib.unwrap(urllib.toBytes(url))
        fp = self.open(url, data)
        headers = fp.info()

        # gPodder TODO: we can get the real url via fp.geturl() here
        #               (if anybody wants to fix filenames in the future)

        result = filename, headers
        bs = 1024*8
        size = -1
        read = current_size
        blocknum = int(current_size/bs)
        if reporthook:
            if "content-length" in headers:
                size = int(headers["Content-Length"]) + current_size
            reporthook(blocknum, bs, size)
        while 1:
            block = fp.read(bs)
            if block == "":
                break
            read += len(block)
            tfp.write(block)
            blocknum += 1
            if reporthook:
                reporthook(blocknum, bs, size)
        fp.close()
        tfp.close()
        del fp
        del tfp

        # raise exception if actual size does not match content-length header
        if size >= 0 and read < size:
            raise urllib.ContentTooShortError("retrieval incomplete: got only %i out "
                                       "of %i bytes" % (read, size), result)

        return result

# end code based on urllib.py

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

        if gpodder.interface == gpodder.MAEMO:
            # Only update status every 3 seconds on Maemo
            self.MAX_UPDATES_PER_SEC = 1./3.

        self.channel = channel
        self.episode = episode

        self.notification = notification

        self.url = self.episode.url
        self.filename = self.episode.local_filename(create=True)
        # Commit the database, so we won't lose the (possibly created) filename
        db.commit()

        self.tempname = self.filename + '.partial'

        # Make an educated guess about the total file size
        self.total_size = self.episode.length

        self.cancelled = False
        self.keep_files = False
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

    def cancel(self, keep_files=False):
        self.cancelled = True
        self.keep_files = keep_files

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

            try:
                self.progress = 100.0*float(count*blockSize)/float(totalSize)
            except ZeroDivisionError, zde:
                log('Totalsize unknown, cannot determine progress.', sender=self)
                self.progress = 100.0
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
            if not self.keep_files:
                util.delete_file(self.tempname)
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

        if os.path.exists(self.tempname):
            try:
                already_downloaded = os.path.getsize(self.tempname)
                if self.total_size > 0:
                    self.progress = already_downloaded/self.total_size

                if already_downloaded > 0:
                    self.speed = _('Queued (partial)')
            except:
                pass
        else:
            # "touch self.tempname", so we also get partial
            # files for resuming when the file is queued
            open(self.tempname, 'w').close()

        # Initial status update
        services.download_status_manager.update_status( self.download_id, episode = self.episode.title, url = self.episode.url, speed = self.speed, progress = self.progress)

        acquired = services.download_status_manager.s_acquire()
        try:
            try:
                if self.cancelled:
                    # Remove the partial file in case we do
                    # not want to keep it (e.g. user cancelled)
                    if not self.keep_files:
                        util.delete_file(self.tempname)
                    return
         
                (unused, headers) = self.downloader.retrieve_resume(resolver.get_real_download_url(self.url), self.tempname, reporthook=self.status_updated)

                new_mimetype = headers.get('content-type', self.episode.mimetype)
                old_mimetype = self.episode.mimetype
                if new_mimetype != old_mimetype:
                    log('Correcting mime type: %s => %s', old_mimetype, new_mimetype, sender=self)
                    old_extension = self.episode.extension()
                    self.episode.mimetype = new_mimetype
                    new_extension = self.episode.extension()

                    # If the desired filename extension changed due to the new mimetype,
                    # we force an update of the local filename to fix the extension
                    if old_extension != new_extension:
                        self.filename = self.episode.local_filename(create=True, force_update=True)

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
            if not self.keep_files:
                util.delete_file(self.tempname)
        except IOError, ioe:
            if self.notification is not None:
                title = ioe.strerror
                message = _('An error happened while trying to download <b>%s</b>. Please try again later.') % ( saxutils.escape( self.episode.title), )
                self.notification( message, title)
            log( 'Error "%s" while downloading "%s": %s', ioe.strerror, self.episode.title, ioe.filename, sender = self)
        except gPodderDownloadHTTPError, gdhe:
            if self.notification is not None:
                title = gdhe.error_message
                message = _('An error (HTTP %d) happened while trying to download <b>%s</b>. You can try to resume the download later.') % ( gdhe.error_code, saxutils.escape( self.episode.title), )
                self.notification( message, title)
            log( 'HTTP error %s while downloading "%s": %s', gdhe.error_code, self.episode.title, gdhe.error_message, sender=self)
        except:
            log( 'Error while downloading "%s".', self.episode.title, sender = self, traceback = True)

