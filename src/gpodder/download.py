# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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
#  download.py -- Download queue management
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#

import glob
import logging
import mimetypes
import os
import os.path
import shutil
import threading
import time
import urllib.error
from abc import ABC, abstractmethod

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, HTTPError, RequestException
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.util.retry import Retry

import gpodder
from gpodder import registry, util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

REDIRECT_RETRIES = 3


class CustomDownload(ABC):
    """ abstract class for custom downloads. DownloadTask call retrieve_resume() on it """

    @property
    @abstractmethod
    def partial_filename(self):
        """
        Full path to the temporary file actually being downloaded (downloaders
        may not support setting a tempname).
        """
        ...

    @partial_filename.setter
    @abstractmethod
    def partial_filename(self, val):
        ...

    @abstractmethod
    def retrieve_resume(self, tempname, reporthook):
        """
        :param str tempname: temporary filename for the download
        :param func(number, number, number) reporthook: callback for download progress (count, blockSize, totalSize)
        :return dict(str, str), str: (headers, real_url)
        """
        return {}, None


class CustomDownloader(ABC):
    """
    abstract class for custom downloaders.

    DownloadTask calls custom_downloader to get a CustomDownload
    """

    @abstractmethod
    def custom_downloader(self, config, episode):
        """
        if this custom downloader has a custom download method (e.g. youtube-dl),
        return a CustomDownload. Else return None
        :param config: gpodder config (e.g. to get preferred video format)
        :param model.PodcastEpisode episode: episode to download
        :return CustomDownload: object used to download the episode
        """
        return None


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
            # Unparsable
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
            return cls(start, end - 1, length)


class DownloadCancelledException(Exception): pass


class DownloadNoURLException(Exception): pass


class gPodderDownloadHTTPError(Exception):
    def __init__(self, url, error_code, error_message):
        self.url = url
        self.error_code = error_code
        self.error_message = error_message


class DownloadURLOpener:

    # Sometimes URLs are not escaped correctly - try to fix them
    # (see RFC2396; Section 2.4.3. Excluded US-ASCII Characters)
    # FYI: The omission of "%" in the list is to avoid double escaping!
    ESCAPE_CHARS = dict((ord(c), '%%%x' % ord(c)) for c in ' <>#"{}|\\^[]`')

    def __init__(self, channel, max_retries=3):
        super().__init__()
        self.channel = channel
        self.max_retries = max_retries

    def init_session(self):
        """ init a session with our own retry codes + retry count """
        # I add a few retries for redirects but it means that I will allow max_retries + REDIRECT_RETRIES
        # if encountering max_retries connect and REDIRECT_RETRIES read for instance
        retry_strategy = Retry(
            total=self.max_retries + REDIRECT_RETRIES,
            connect=self.max_retries,
            read=self.max_retries,
            redirect=max(REDIRECT_RETRIES, self.max_retries),
            status=self.max_retries,
            status_forcelist=Retry.RETRY_AFTER_STATUS_CODES.union((408, 418, 504, 598, 599,)))
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)
        return http

# The following is based on Python's urllib.py "URLopener.retrieve"
# Also based on http://mail.python.org/pipermail/python-list/2001-October/110069.html

    def retrieve_resume(self, url, filename, reporthook=None, data=None, disable_auth=False):
        """Download files from an URL; return (headers, real_url)

        Resumes a download if the local filename exists and
        the server supports download resuming.
        """

        current_size = 0
        tfp = None
        headers = {
            'User-agent': gpodder.user_agent
        }

        if (self.channel.auth_username or self.channel.auth_password) and not disable_auth:
            logger.debug('Authenticating as "%s"', self.channel.auth_username)
            auth = (self.channel.auth_username, self.channel.auth_password)
        else:
            auth = None

        if os.path.exists(filename):
            try:
                current_size = os.path.getsize(filename)
                tfp = open(filename, 'ab')
                # If the file exists, then only download the remainder
                if current_size > 0:
                    headers['Range'] = 'bytes=%s-' % (current_size)
            except:
                logger.warning('Cannot resume download: %s', filename, exc_info=True)
                tfp = None
                current_size = 0

        if tfp is None:
            tfp = open(filename, 'wb')

        # Fix a problem with bad URLs that are not encoded correctly (bug 549)
        url = url.translate(self.ESCAPE_CHARS)

        session = self.init_session()
        with session.get(url,
                         headers=headers,
                         stream=True,
                         auth=auth,
                         timeout=gpodder.SOCKET_TIMEOUT) as resp:
            try:
                resp.raise_for_status()
            except HTTPError as e:
                if auth is not None:
                    # Try again without authentication (bug 1296)
                    return self.retrieve_resume(url, filename, reporthook, data, True)
                else:
                    raise gPodderDownloadHTTPError(url, resp.status_code, str(e))

            headers = resp.headers

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
                    logger.warning('Cannot resume: Invalid Content-Range (RFC2616).')

            result = headers, resp.url
            bs = 1024 * 8
            size = -1
            read = current_size
            blocknum = current_size // bs
            if reporthook:
                if "content-length" in headers:
                    size = int(headers['content-length']) + current_size
                reporthook(blocknum, bs, size)
            for block in resp.iter_content(bs):
                read += len(block)
                tfp.write(block)
                blocknum += 1
                if reporthook:
                    reporthook(blocknum, bs, size)
            tfp.close()
            del tfp

        # raise exception if actual size does not match content-length header
        if size >= 0 and read < size:
            raise urllib.error.ContentTooShortError("retrieval incomplete: got only %i out "
                                       "of %i bytes" % (read, size), result)

        return result

# end code based on urllib.py


class DefaultDownload(CustomDownload):
    def __init__(self, config, episode, url):
        self._config = config
        self.__episode = episode
        self._url = url
        self.__partial_filename = None

    @property
    def partial_filename(self):
        return self.__partial_filename

    @partial_filename.setter
    def partial_filename(self, val):
        self.__partial_filename = val

    def retrieve_resume(self, tempname, reporthook):
        url = self._url
        logger.info("Downloading %s", url)
        max_retries = max(0, self._config.auto.retries)
        downloader = DownloadURLOpener(self.__episode.channel, max_retries=max_retries)
        self.partial_filename = tempname

        # Retry the download on incomplete download (other retries are done by the Retry strategy)
        for retry in range(max_retries + 1):
            if retry > 0:
                logger.info('Retrying download of %s (%d)', url, retry)
                time.sleep(1)

            try:
                headers, real_url = downloader.retrieve_resume(url,
                    tempname, reporthook=reporthook)
                # If we arrive here, the download was successful
                break
            except urllib.error.ContentTooShortError as ctse:
                if retry < max_retries:
                    logger.info('Content too short: %s - will retry.',
                            url)
                    continue
                raise
        return (headers, real_url)


class DefaultDownloader(CustomDownloader):
    @staticmethod
    def custom_downloader(config, episode):
        url = episode.url
        # Resolve URL and start downloading the episode
        res = registry.download_url.resolve(config, None, episode, False)
        if res:
            url = res
        if url == episode.url:
            # don't modify custom urls (#635 - vimeo breaks if * is unescaped)
            url = url.strip()
            url = util.iri_to_url(url)
        return DefaultDownload(config, episode, url)


class DownloadQueueWorker(object):
    def __init__(self, queue, exit_callback, continue_check_callback):
        self.queue = queue
        self.exit_callback = exit_callback
        self.continue_check_callback = continue_check_callback

    def __repr__(self):
        return threading.current_thread().getName()

    def run(self):
        logger.info('Starting new thread: %s', self)
        while True:
            if not self.continue_check_callback(self):
                return

            task = self.queue.get_next() if self.queue.enabled else None
            if not task:
                logger.info('No more tasks for %s to carry out.', self)
                break
            logger.info('%s is processing: %s', self, task)
            task.run()
            task.recycle()

        self.exit_callback(self)


class ForceDownloadWorker(object):
    def __init__(self, task):
        self.task = task

    def __repr__(self):
        return threading.current_thread().getName()

    def run(self):
        logger.info('Starting new thread: %s', self)
        logger.info('%s is processing: %s', self, self.task)
        self.task.run()
        self.task.recycle()


class DownloadQueueManager(object):
    def __init__(self, config, queue):
        self._config = config
        self.tasks = queue

        self.worker_threads_access = threading.RLock()
        self.worker_threads = []

    def disable(self):
        self.tasks.enabled = False

    def enable(self):
        self.tasks.enabled = True
        self.__spawn_threads()

    def __exit_callback(self, worker_thread):
        with self.worker_threads_access:
            self.worker_threads.remove(worker_thread)

    def __continue_check_callback(self, worker_thread):
        with self.worker_threads_access:
            if len(self.worker_threads) > self._config.limit.downloads.concurrent and \
                    self._config.limit.downloads.enabled:
                self.worker_threads.remove(worker_thread)
                return False
            else:
                return True

    def __spawn_threads(self):
        """Spawn new worker threads if necessary
        """
        if not self.tasks.enabled:
            return

        with self.worker_threads_access:
            work_count = self.tasks.available_work_count()
            if self._config.limit.downloads.enabled:
                # always allow at least 1 download
                spawn_limit = max(int(self._config.limit.downloads.concurrent), 1)
            else:
                spawn_limit = self._config.limit.downloads.concurrent_max
            running = len(self.worker_threads)
            logger.info('%r tasks to do, can start at most %r threads, %r threads currently running', work_count, spawn_limit, running)
            for i in range(0, min(work_count, spawn_limit - running)):
                # We have to create a new thread here, there's work to do
                logger.info('Starting new worker thread.')

                worker = DownloadQueueWorker(self.tasks, self.__exit_callback,
                        self.__continue_check_callback)
                self.worker_threads.append(worker)
                util.run_in_background(worker.run)

    def update_max_downloads(self):
        self.__spawn_threads()

    def force_start_task(self, task):
        with task:
            if task.status in (task.QUEUED, task.PAUSED, task.CANCELLED, task.FAILED):
                task.status = task.DOWNLOADING
                worker = ForceDownloadWorker(task)
                util.run_in_background(worker.run)

    def queue_task(self, task):
        """Marks a task as queued
        """
        self.tasks.queue_task(task)
        self.__spawn_threads()

    def has_workers(self):
        return len(self.worker_threads) > 0


class DownloadTask(object):
    """An object representing the download task of an episode

    You can create a new download task like this:

        task = DownloadTask(episode, gpodder.config.Config(CONFIGFILE))
        task.status = DownloadTask.QUEUED
        task.run()

    While the download is in progress, you can access its properties:

        task.total_size       # in bytes
        task.progress         # from 0.0 to 1.0
        task.speed            # in bytes per second
        str(task)             # name of the episode
        task.status           # current status
        task.status_changed   # True if the status has been changed (see below)
        task.url              # URL of the episode being downloaded
        task.podcast_url      # URL of the podcast this download belongs to
        task.episode          # Episode object of this task

    You can cancel a running download task by setting its status:

        with task:
            task.status = DownloadTask.CANCELLING

    The task will then abort as soon as possible (due to the nature
    of downloading data, this can take a while when the Internet is
    busy).

    The "status_changed" attribute gets set to True every time the
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

    The UI can call the method "notify_as_finished()" to determine if
    this episode still has still to be shown as "finished" download
    in a notification window. This will return True only the first time
    it is called when the status is DONE. After returning True once,
    it will always return False afterwards.

    The same thing works for failed downloads ("notify_as_failed()").
    """
    # Possible states this download task can be in
    STATUS_MESSAGE = (_('Queued'), _('Queued'), _('Downloading'),
            _('Finished'), _('Failed'), _('Cancelling'), _('Cancelled'), _('Pausing'), _('Paused'))
    (NEW, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLING, CANCELLED, PAUSING, PAUSED) = list(range(9))

    # Whether this task represents a file download or a device sync operation
    ACTIVITY_DOWNLOAD, ACTIVITY_SYNCHRONIZE = list(range(2))

    # Minimum time between progress updates (in seconds)
    MIN_TIME_BETWEEN_UPDATES = 1.

    def __str__(self):
        return self.__episode.title

    def __enter__(self):
        return self.__lock.acquire()

    def __exit__(self, type, value, traceback):
        self.__lock.release()

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

    def __get_activity(self):
        return self.__activity

    def __set_activity(self, activity):
        self.__activity = activity

    activity = property(fget=__get_activity, fset=__set_activity)

    def __get_url(self):
        return self.__episode.url

    url = property(fget=__get_url)

    def __get_podcast_url(self):
        return self.__episode.channel.url

    podcast_url = property(fget=__get_podcast_url)

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def __get_downloader(self):
        return self.__downloader

    def __set_downloader(self, downloader):
        # modifying the downloader will only have effect before the download is started
        self.__downloader = downloader

    downloader = property(fget=__get_downloader, fset=__set_downloader)

    def can_queue(self):
        return self.status in (self.CANCELLED, self.PAUSED, self.FAILED)

    def unpause(self):
        with self:
            # Resume a downloading task that was transitioning to paused
            if self.status == self.PAUSING:
                self.status = self.DOWNLOADING

    def can_pause(self):
        return self.status in (self.DOWNLOADING, self.QUEUED)

    def pause(self):
        with self:
            # Pause a queued download
            if self.status == self.QUEUED:
                self.status = self.PAUSED
            # Request pause of a running download
            elif self.status == self.DOWNLOADING:
                self.status = self.PAUSING
                # download rate limited tasks sleep and take longer to transition from the PAUSING state to the PAUSED state

    def can_cancel(self):
        return self.status in (self.DOWNLOADING, self.QUEUED, self.PAUSED, self.FAILED)

    def cancel(self):
        with self:
            # Cancelling directly is allowed if the task isn't currently downloading
            if self.status in (self.QUEUED, self.PAUSED, self.FAILED):
                self.status = self.CANCELLING
                # Call run, so the partial file gets deleted, and task recycled
                self.run()
            # Otherwise request cancellation
            elif self.status == self.DOWNLOADING:
                self.status = self.CANCELLING

    def can_remove(self):
        return self.status in (self.CANCELLED, self.FAILED, self.DONE)

    def delete_partial_files(self):
        temporary_files = [self.tempname]
        # youtube-dl creates .partial.* files for adaptive formats
        temporary_files += glob.glob('%s.*' % self.tempname)

        for tempfile in temporary_files:
            util.delete_file(tempfile)

    def removed_from_list(self):
        if self.status != self.DONE:
            self.delete_partial_files()

    def __init__(self, episode, config, downloader=None):
        assert episode.download_task is None
        self.__lock = threading.RLock()
        self.__status = DownloadTask.NEW
        self.__activity = DownloadTask.ACTIVITY_DOWNLOAD
        self.__status_changed = True
        self.__episode = episode
        self._config = config
        # specify a custom downloader to be used for this download
        self.__downloader = downloader

        # Create the target filename and save it in the database
        self.filename = self.__episode.local_filename(create=True)
        self.tempname = self.filename + '.partial'

        self.total_size = self.__episode.file_size
        self.speed = 0.0
        self.progress = 0.0
        self.error_message = None
        self.custom_downloader = None

        # Have we already shown this task in a notification?
        self._notification_shown = False

        # Variables for speed limit and speed calculation
        self.__start_time = 0
        self.__start_blocks = 0
        self.__limit_rate_value = self._config.limit.bandwidth.kbps
        self.__limit_rate = self._config.limit.bandwidth.enabled

        # Progress update functions
        self._progress_updated = None
        self._last_progress_updated = 0.

        # If the tempname already exists, set progress accordingly
        if os.path.exists(self.tempname):
            try:
                already_downloaded = os.path.getsize(self.tempname)
                if self.total_size > 0:
                    self.progress = max(0.0, min(1.0, already_downloaded / self.total_size))
            except OSError as os_error:
                logger.error('Cannot get size for %s', os_error)
        else:
            # "touch self.tempname", so we also get partial
            # files for resuming when the file is queued
            open(self.tempname, 'w').close()

        # Store a reference to this task in the episode
        episode.download_task = self

    def reuse(self):
        if not os.path.exists(self.tempname):
            # partial file was deleted when cancelled, recreate it
            open(self.tempname, 'w').close()

    def notify_as_finished(self):
        if self.status == DownloadTask.DONE:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def notify_as_failed(self):
        if self.status == DownloadTask.FAILED:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def add_progress_callback(self, callback):
        self._progress_updated = callback

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)
            if self.__episode.file_size != self.total_size:
                logger.debug('Updating file size of %s to %s',
                        self.filename, self.total_size)
                self.__episode.file_size = self.total_size
                self.__episode.save()

        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, count * blockSize / self.total_size))
            if self._progress_updated is not None:
                diff = time.time() - self._last_progress_updated
                if diff > self.MIN_TIME_BETWEEN_UPDATES or self.progress == 1.:
                    self._progress_updated(self.progress)
                    self._last_progress_updated = time.time()

        self.calculate_speed(count, blockSize)

        if self.status == DownloadTask.CANCELLING:
            raise DownloadCancelledException()

        if self.status == DownloadTask.PAUSING:
            raise DownloadCancelledException()

    def calculate_speed(self, count, blockSize):
        if count % 5 == 0:
            now = time.time()
            if self.__start_time > 0:
                # Has rate limiting been enabled or disabled?
                if self.__limit_rate != self._config.limit.bandwidth.enabled:
                    # If it has been enabled then reset base time and block count
                    if self._config.limit.bandwidth.enabled:
                        self.__start_time = now
                        self.__start_blocks = count
                    self.__limit_rate = self._config.limit.bandwidth.enabled

                # Has the rate been changed and are we currently limiting?
                if self.__limit_rate_value != self._config.limit.bandwidth.kbps and self.__limit_rate:
                    self.__start_time = now
                    self.__start_blocks = count
                    self.__limit_rate_value = self._config.limit.bandwidth.kbps

                passed = now - self.__start_time
                if passed > 0:
                    speed = ((count - self.__start_blocks) * blockSize) / passed
                else:
                    speed = 0
            else:
                self.__start_time = now
                self.__start_blocks = count
                passed = now - self.__start_time
                speed = count * blockSize

            self.speed = float(speed)

            if self._config.limit.bandwidth.enabled and speed > self._config.limit.bandwidth.kbps:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                should_have_passed = (count - self.__start_blocks) * blockSize / (self._config.limit.bandwidth.kbps * 1024.0)
                if should_have_passed > passed:
                    # sleep a maximum of 10 seconds to not cause time-outs
                    delay = min(10.0, float(should_have_passed - passed))
                    time.sleep(delay)

    def recycle(self):
        if self.status not in (self.FAILED, self.PAUSED):
            self.episode.download_task = None

    def set_episode_download_task(self):
        if not self.episode.download_task:
            self.episode.download_task = self

    def run(self):
        # Speed calculation (re-)starts here
        self.__start_time = 0
        self.__start_blocks = 0

        # If the download has already been cancelled/paused, skip it
        with self:
            if self.status == DownloadTask.CANCELLING:
                self.status = DownloadTask.CANCELLED
                self.__episode._download_error = None
                self.delete_partial_files()
                self.progress = 0.0
                self.speed = 0.0
                self.recycle()
                return False

            if self.status == DownloadTask.PAUSING:
                self.status = DownloadTask.PAUSED
                return False

            # We only start this download if its status is downloading
            if self.status != DownloadTask.DOWNLOADING:
                return False

            # We are downloading this file right now
            self._notification_shown = False

            # Restore a reference to this task in the episode
            # when running a recycled task following a pause or failed
            # see #649
            self.set_episode_download_task()

        url = self.__episode.url
        result = DownloadTask.DOWNLOADING
        try:
            if url == '':
                raise DownloadNoURLException()

            if self.downloader:
                downloader = self.downloader.custom_downloader(self._config, self.episode)
            else:
                downloader = registry.custom_downloader.resolve(self._config, None, self.episode)

            if downloader:
                logger.info('Downloading %s with %s', url, downloader)
            else:
                downloader = DefaultDownloader.custom_downloader(self._config, self.episode)

            self.custom_downloader = downloader
            headers, real_url = downloader.retrieve_resume(self.tempname, self.status_updated)

            new_mimetype = headers.get('content-type', self.__episode.mime_type)
            old_mimetype = self.__episode.mime_type
            _basename, ext = os.path.splitext(self.filename)
            if new_mimetype != old_mimetype or util.wrong_extension(ext):
                logger.info('Updating mime type: %s => %s', old_mimetype, new_mimetype)
                old_extension = self.__episode.extension()
                self.__episode.mime_type = new_mimetype
                # don't call local_filename because we'll get the old download name
                new_extension = self.__episode.extension(may_call_local_filename=False)

                # If the desired filename extension changed due to the new
                # mimetype, we force an update of the local filename to fix the
                # extension.
                if old_extension != new_extension or util.wrong_extension(ext):
                    self.filename = self.__episode.local_filename(create=True, force_update=True)

            # In some cases, the redirect of a URL causes the real filename to
            # be revealed in the final URL (e.g. http://gpodder.org/bug/1423)
            if real_url != url and not util.is_known_redirecter(real_url):
                realname, realext = util.filename_from_url(real_url)

                # Only update from redirect if the redirected-to filename has
                # a proper extension (this is needed for e.g. YouTube)
                if not util.wrong_extension(realext):
                    real_filename = ''.join((realname, realext))
                    self.filename = self.__episode.local_filename(create=True,
                            force_update=True, template=real_filename)
                    logger.info('Download was redirected (%s). New filename: %s',
                            real_url, os.path.basename(self.filename))

            # Look at the Content-disposition header; use if if available
            disposition_filename = util.get_header_param(headers, 'filename', 'content-disposition')

            # Some servers do send the content-disposition header, but provide
            # an empty filename, resulting in an empty string here (bug 1440)
            if disposition_filename is not None and disposition_filename != '':
                # The server specifies a download filename - try to use it
                # filename_from_url to remove query string; see #591
                fn, ext = util.filename_from_url(disposition_filename)
                logger.debug("converting disposition filename '%s' to local filename '%s%s'", disposition_filename, fn, ext)
                disposition_filename = fn + ext
                self.filename = self.__episode.local_filename(create=True,
                        force_update=True, template=disposition_filename)
                new_mimetype, encoding = mimetypes.guess_type(self.filename)
                if new_mimetype is not None:
                    logger.info('Using content-disposition mimetype: %s',
                            new_mimetype)
                    self.__episode.mime_type = new_mimetype

            # Re-evaluate filename and tempname to take care of podcast renames
            # while downloads are running (which will change both file names)
            self.filename = self.__episode.local_filename(create=False)
            self.tempname = os.path.join(os.path.dirname(self.filename),
                    os.path.basename(self.tempname))
            shutil.move(self.tempname, self.filename)

            # Model- and database-related updates after a download has finished
            self.__episode.on_downloaded(self.filename)
        except DownloadCancelledException:
            logger.info('Download has been cancelled/paused: %s', self)
            if self.status == DownloadTask.CANCELLING:
                self.__episode._download_error = None
                self.delete_partial_files()
                self.progress = 0.0
                self.speed = 0.0
            result = DownloadTask.CANCELLED
        except DownloadNoURLException:
            result = DownloadTask.FAILED
            self.error_message = _('Episode has no URL to download')
        except urllib.error.ContentTooShortError as ctse:
            result = DownloadTask.FAILED
            self.error_message = _('Missing content from server')
        except ConnectionError as ce:
            # special case request exception
            result = DownloadTask.FAILED
            logger.error('Download failed: %s', str(ce))
            d = {'host': ce.args[0].pool.host, 'port': ce.args[0].pool.port}
            self.error_message = _("Couldn't connect to server %(host)s:%(port)s" % d)
        except RequestException as re:
            # extract MaxRetryError to shorten the exception message
            if isinstance(re.args[0], MaxRetryError):
                re = re.args[0]
            logger.error('%s while downloading "%s"', str(re),
                    self.__episode.title)
            result = DownloadTask.FAILED
            d = {'error': str(re)}
            self.error_message = _('Request Error: %(error)s') % d
        except IOError as ioe:
            logger.error('%s while downloading "%s": %s', ioe.strerror,
                    self.__episode.title, ioe.filename)
            result = DownloadTask.FAILED
            d = {'error': ioe.strerror, 'filename': ioe.filename}
            self.error_message = _('I/O Error: %(error)s: %(filename)s') % d
        except gPodderDownloadHTTPError as gdhe:
            logger.error('HTTP %s while downloading "%s": %s',
                    gdhe.error_code, self.__episode.title, gdhe.error_message)
            result = DownloadTask.FAILED
            d = {'code': gdhe.error_code, 'message': gdhe.error_message}
            self.error_message = _('HTTP Error %(code)s: %(message)s') % d
        except Exception as e:
            result = DownloadTask.FAILED
            logger.error('Download failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        with self:
            if result == DownloadTask.DOWNLOADING:
                # Everything went well - we're done (even if the task was cancelled/paused,
                # since it's finished we might as well mark it done)
                self.status = DownloadTask.DONE
                if self.total_size <= 0:
                    self.total_size = util.calculate_size(self.filename)
                    logger.info('Total size updated to %d', self.total_size)
                self.progress = 1.0
                gpodder.user_extensions.on_episode_downloaded(self.__episode)
                return True

            self.speed = 0.0

            if result == DownloadTask.FAILED:
                self.status = DownloadTask.FAILED
                self.__episode._download_error = self.error_message

            # cancelled/paused -- update state to mark it as safe to manipulate this task again
            elif self.status == DownloadTask.PAUSING:
                self.status = DownloadTask.PAUSED
            elif self.status == DownloadTask.CANCELLING:
                self.status = DownloadTask.CANCELLED

        # We finished, but not successfully (at least not really)
        return False
