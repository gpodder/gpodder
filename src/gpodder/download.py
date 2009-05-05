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

from __future__ import with_statement

from gpodder.liblogger import log
from gpodder.libgpodder import gl
from gpodder.dbsqlite import db
from gpodder import util
from gpodder import resolver
import gpodder

import threading
import urllib
import shutil
import os.path
import os
import time
import collections

from xml.sax import saxutils


class ContentRange(object):
    # Based on:
    # http://svn.pythonpaste.org/Paste/WebOb/trunk/webob/byterange.py
    #
    # Copyright (c) 2007 Ian Bicking and Contributors
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the
    # "Software"), to deal in the Software without restriction, including
    # without limitation the rights to use, copy, modify, merge, publish,
    # distribute, sublicense, and/or sell copies of the Software, and to
    # permit persons to whom the Software is furnished to do so, subject to
    # the following conditions:
    #
    # The above copyright notice and this permission notice shall be
    # included in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    # LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    # OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    # WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """
    Represents the Content-Range header

    This header is ``start-stop/length``, where stop and length can be
    ``*`` (represented as None in the attributes).
    """

    def __init__(self, start, stop, length):
        assert start >= 0, "Bad start: %r" % start
        assert stop is None or (stop >= 0 and stop >= start), (
            "Bad stop: %r" % stop)
        self.start = start
        self.stop = stop
        self.length = length

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            self)

    def __str__(self):
        if self.stop is None:
            stop = '*'
        else:
            stop = self.stop + 1
        if self.length is None:
            length = '*'
        else:
            length = self.length
        return 'bytes %s-%s/%s' % (self.start, stop, length)

    def __iter__(self):
        """
        Mostly so you can unpack this, like:

            start, stop, length = res.content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value):
        """
        Parse the header.  May return None if it cannot parse.
        """
        if value is None:
            return None
        value = value.strip()
        if not value.startswith('bytes '):
            # Unparseable
            return None
        value = value[len('bytes '):].strip()
        if '/' not in value:
            # Invalid, no length given
            return None
        range, length = value.split('/', 1)
        if '-' not in range:
            # Invalid, no range
            return None
        start, end = range.split('-', 1)
        try:
            start = int(start)
            if end == '*':
                end = None
            else:
                end = int(end)
            if length == '*':
                length = None
            else:
                length = int(length)
        except ValueError:
            # Parse problem
            return None
        if end is None:
            return cls(start, None, length)
        else:
            return cls(start, end-1, length)


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

        if current_size > 0:
            # We told the server to resume - see if she agrees
            # See RFC2616 (206 Partial Content + Section 14.16)
            # XXX check status code here, too...
            range = ContentRange.parse(headers.get('content-range', ''))
            if range is None or range.start != current_size:
                # Ok, that did not work. Reset the download
                # TODO: seek and truncate if content-range differs from request
                tfp.close()
                tfp = open(filename, 'wb')
                current_size = 0
                log('Cannot resume. Missing or wrong Content-Range header (RFC2616)', sender=self)


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


class DownloadQueueWorker(threading.Thread):
    def __init__(self, queue, exit_callback):
        threading.Thread.__init__(self)
        self.queue = queue
        self.exit_callback = exit_callback
        self.cancelled = False

    def stop_accepting_tasks(self):
        """
        When this is called, the worker will not accept new tasks,
        but quit when the current task has been finished.
        """
        if not self.cancelled:
            self.cancelled = True
            log('%s stopped accepting tasks.', self.getName(), sender=self)

    def run(self):
        log('Running new thread: %s', self.getName(), sender=self)
        while not self.cancelled:
            try:
                task = self.queue.pop()
                log('%s is processing: %s', self.getName(), task, sender=self)
                task.run()
            except IndexError, e:
                log('No more tasks for %s to carry out.', self.getName(), sender=self)
                break
        self.exit_callback(self)


class DownloadQueueManager(object):
    def __init__(self, download_status_manager):
        self.download_status_manager = download_status_manager
        self.tasks = collections.deque()

        self.worker_threads_access = threading.RLock()
        self.worker_threads = []

    def __exit_callback(self, worker_thread):
        with self.worker_threads_access:
            self.worker_threads.remove(worker_thread)

    def spawn_and_retire_threads(self, request_new_thread=False):
        with self.worker_threads_access:
            if len(self.worker_threads) > gl.config.max_downloads and \
                    gl.config.max_downloads_enabled:
                # Tell the excessive amount of oldest worker threads to quit, but keep at least one
                count = min(len(self.worker_threads)-1, len(self.worker_threads)-gl.config.max_downloads)
                for worker in self.worker_threads[:count]:
                    worker.stop_accepting_tasks()

            if request_new_thread and (len(self.worker_threads) == 0 or \
                    len(self.worker_threads) < gl.config.max_downloads or \
                    not gl.config.max_downloads_enabled):
                # We have to create a new thread here, there's work to do
                log('I am going to spawn a new worker thread.', sender=self)
                worker = DownloadQueueWorker(self.tasks, self.__exit_callback)
                self.worker_threads.append(worker)
                worker.start()

    def add_resumed_task(self, task):
        """Simply add the task without starting the download"""
        self.download_status_manager.register_task(task)

    def add_task(self, task):
        if task.status == DownloadTask.INIT:
            # This task is fresh, so add it to our status manager
            self.download_status_manager.register_task(task)
        else:
            # This task is old so update episode from db
            task.episode.reload_from_db()
        task.status = DownloadTask.QUEUED
        self.tasks.appendleft(task)
        self.spawn_and_retire_threads(request_new_thread=True)


class DownloadTask(object):
    """An object representing the download task of an episode

    You can create a new download task like this:

        task = DownloadTask(episode)
        task.status = DownloadTask.QUEUED
        task.run()

    While the download is in progress, you can access its properties:

        task.total_size       # in bytes
        task.progress         # from 0.0 to 1.0
        task.speed            # in bytes per second
        str(task)             # name of the episode
        task.status           # current status
        task.status_changed   # True if the status has been changed

    You can cancel a running download task by setting its status:

        task.status = DownloadTask.CANCELLED

    The task will then abort as soon as possible (due to the nature
    of downloading data, this can take a while when the Internet is
    busy).

    The "status_changed" attribute gets set to True everytime the
    "status" attribute changes its value. After you get the value of
    the "status_changed" attribute, it is always reset to False:

        if task.status_changed:
            new_status = task.status
            # .. update the UI accordingly ..

    Obviously, this also means that you must have at most *one*
    place in your UI code where you check for status changes and
    broadcast the status updates from there.

    While the download is taking place and after the .run() method
    has finished, you can get the final status to check if the download
    was successful:

        if task.status == DownloadTask.DONE:
            # .. everything ok ..
        elif task.status == DownloadTask.FAILED:
            # .. an error happened, and the
            #    error_message attribute is set ..
            print task.error_message
        elif task.status == DownloadTask.PAUSED:
            # .. user paused the download ..
        elif task.status == DownloadTask.CANCELLED:
            # .. user cancelled the download ..

    The difference between cancelling and pausing a DownloadTask is
    that the temporary file gets deleted when cancelling, but does
    not get deleted when pausing.

    Be sure to call .removed_from_list() on this task when removing
    it from the UI, so that it can carry out any pending clean-up
    actions (e.g. removing the temporary file when the task has not
    finished successfully; i.e. task.status != DownloadTask.DONE).
    """
    # Possible states this download task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Downloading'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLED, PAUSED) = range(7)

    def __str__(self):
        return self.__episode.title

    def __get_status(self):
        return self.__status

    def __set_status(self, status):
        if status != self.__status:
            self.__status_changed = True
            self.__status = status

    status = property(fget=__get_status, fset=__set_status)

    def __get_status_changed(self):
        if self.__status_changed:
            self.__status_changed = False
            return True
        else:
            return False

    status_changed = property(fget=__get_status_changed)

    def __get_url(self):
        return self.__episode.url

    url = property(fget=__get_url)

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def removed_from_list(self):
        if self.status != self.DONE:
            util.delete_file(self.tempname)

    def __init__(self, episode):
        self.__status = DownloadTask.INIT
        self.__status_changed = True
        self.__episode = episode

        # Create the target filename and save it in the database
        self.filename = self.__episode.local_filename(create=True)
        self.tempname = self.filename + '.partial'
        db.commit()

        self.total_size = self.__episode.length
        self.speed = 0.0
        self.progress = 0.0
        self.error_message = None

        # Variables for speed limit and speed calculation
        self.__start_time = 0
        self.__start_blocks = 0
        self.__limit_rate_value = gl.config.limit_rate_value
        self.__limit_rate = gl.config.limit_rate

        # If the tempname already exists, set progress accordingly
        if os.path.exists(self.tempname):
            try:
                already_downloaded = os.path.getsize(self.tempname)
                if self.total_size > 0:
                    self.progress = max(0.0, min(1.0, float(already_downloaded)/self.total_size))
            except OSError, os_error:
                log('Error while getting size for existing file: %s', os_error, sender=self)
        else:
            # "touch self.tempname", so we also get partial
            # files for resuming when the file is queued
            open(self.tempname, 'w').close()

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)

        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, float(count*blockSize)/self.total_size))

        self.calculate_speed(count, blockSize)

        if self.status == DownloadTask.CANCELLED:
            raise DownloadCancelledException()

        if self.status == DownloadTask.PAUSED:
            raise DownloadCancelledException()

    def calculate_speed(self, count, blockSize):
        if count % 5 == 0:
            now = time.time()
            if self.__start_time > 0:
                # Has rate limiting been enabled or disabled?                
                if self.__limit_rate != gl.config.limit_rate: 
                    # If it has been enabled then reset base time and block count                    
                    if gl.config.limit_rate:
                        self.__start_time = now
                        self.__start_blocks = count
                    self.__limit_rate = gl.config.limit_rate
                    
                # Has the rate been changed and are we currently limiting?            
                if self.__limit_rate_value != gl.config.limit_rate_value and self.__limit_rate: 
                    self.__start_time = now
                    self.__start_blocks = count
                    self.__limit_rate_value = gl.config.limit_rate_value

                passed = now - self.__start_time
                if passed > 0:
                    speed = ((count-self.__start_blocks)*blockSize)/passed
                else:
                    speed = 0
            else:
                self.__start_time = now
                self.__start_blocks = count
                passed = now - self.__start_time
                speed = count*blockSize

            self.speed = float(speed)

            if gl.config.limit_rate and speed > gl.config.limit_rate_value:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                should_have_passed = float((count-self.__start_blocks)*blockSize)/(gl.config.limit_rate_value*1024.0)
                if should_have_passed > passed:
                    # sleep a maximum of 10 seconds to not cause time-outs
                    delay = min(10.0, float(should_have_passed-passed))
                    time.sleep(delay)

    def run(self):
        # Speed calculation (re-)starts here
        self.__start_time = 0
        self.__start_blocks = 0

        # If the download has already been cancelled, skip it
        if self.status == DownloadTask.CANCELLED:
            util.delete_file(self.tempname)
            return False

        # We only start this download if its status is "queued"
        if self.status != DownloadTask.QUEUED:
            return False

        # We are downloading this file right now
        self.status = DownloadTask.DOWNLOADING

        try:
            # Resolve URL and start downloading the episode
            url = resolver.get_real_download_url(self.__episode.url)
            downloader =  DownloadURLOpener(self.__episode.channel)
            (unused, headers) = downloader.retrieve_resume(url,
                    self.tempname, reporthook=self.status_updated)

            new_mimetype = headers.get('content-type', self.__episode.mimetype)
            old_mimetype = self.__episode.mimetype
            if new_mimetype != old_mimetype:
                log('Correcting mime type: %s => %s', old_mimetype, new_mimetype, sender=self)
                old_extension = self.__episode.extension()
                self.__episode.mimetype = new_mimetype
                new_extension = self.__episode.extension()

                # If the desired filename extension changed due to the new mimetype,
                # we force an update of the local filename to fix the extension
                if old_extension != new_extension:
                    self.filename = self.__episode.local_filename(create=True, force_update=True)

            shutil.move(self.tempname, self.filename)

            # Get the _real_ filesize once we actually have the file
            self.__episode.length = os.path.getsize(self.filename)
            self.__episode.channel.addDownloadedItem(self.__episode)
            
            # If a user command has been defined, execute the command setting some environment variables
            if len(gl.config.cmd_download_complete) > 0:
                os.environ["GPODDER_EPISODE_URL"]=self.__episode.url or ''
                os.environ["GPODDER_EPISODE_TITLE"]=self.__episode.title or ''
                os.environ["GPODDER_EPISODE_FILENAME"]=self.filename or ''
                os.environ["GPODDER_EPISODE_PUBDATE"]=str(int(self.__episode.pubDate))
                os.environ["GPODDER_EPISODE_LINK"]=self.__episode.link or ''
                os.environ["GPODDER_EPISODE_DESC"]=self.__episode.description or ''
                util.run_external_command(gl.config.cmd_download_complete)
        except DownloadCancelledException:
            log('Download has been cancelled/paused: %s', self, sender=self)
            if self.status == DownloadTask.CANCELLED:
                util.delete_file(self.tempname)
                self.progress = 0.0
                self.speed = 0.0
        except IOError, ioe:
            log( 'Error "%s" while downloading "%s": %s', ioe.strerror, self.__episode.title, ioe.filename, sender=self)
            self.status = DownloadTask.FAILED
            self.error_message = _('I/O Error: %s: %s') % (ioe.strerror, ioe.filename)
        except gPodderDownloadHTTPError, gdhe:
            log( 'HTTP error %s while downloading "%s": %s', gdhe.error_code, self.__episode.title, gdhe.error_message, sender=self)
            self.status = DownloadTask.FAILED
            self.error_message = _('HTTP Error %s: %s') % (gdhe.error_code, gdhe.error_message)
        except Exception, e:
            self.status = DownloadTask.FAILED
            self.error_message = _('Error: %s') % (e.message,)

        if self.status == DownloadTask.DOWNLOADING:
            # Everything went well - we're done
            self.status = DownloadTask.DONE
            self.progress = 1.0
            return True
        
        self.speed = 0.0

        # We finished, but not successfully (at least not really)
        return False

