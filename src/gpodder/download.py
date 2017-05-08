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
#  download.py -- Download queue management
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#
import logging

from gpodder.task import Task, TaskCancelledException, DOWNLOAD_ACTIVITY
from gpodder import util
from gpodder import youtube
from gpodder import vimeo
from gpodder import escapist_videos
import gpodder

import socket
import urllib.request, urllib.parse, urllib.error
import urllib.parse
import shutil
import os.path
import os
import time

import mimetypes
import email


logger = logging.getLogger(__name__)

_ = gpodder.gettext


def get_header_param(headers, param, header_name):
    """Extract a HTTP header parameter from a dict

    Uses the "email" module to retrieve parameters
    from HTTP headers. This can be used to get the
    "filename" parameter of the "content-disposition"
    header for downloads to pick a good filename.

    Returns None if the filename cannot be retrieved.
    """
    value = None
    try:
        headers_string = ['%s:%s'%(k,v) for k,v in list(headers.items())]
        msg = email.message_from_string('\n'.join(headers_string))
        if header_name in msg:
            raw_value = msg.get_param(param, header=header_name)
            if raw_value is not None:
                value = email.utils.collapse_rfc2231_value(raw_value)
    except Exception as e:
        logger.error('Cannot get %s from %s', param, header_name, exc_info=True)

    return value


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


class AuthenticationError(Exception):
    pass


class gPodderDownloadHTTPError(Exception):
    def __init__(self, url, error_code, error_message):
        self.url = url
        self.error_code = error_code
        self.error_message = error_message


class DownloadURLOpener(urllib.request.FancyURLopener):
    version = gpodder.user_agent

    # Sometimes URLs are not escaped correctly - try to fix them
    # (see RFC2396; Section 2.4.3. Excluded US-ASCII Characters)
    # FYI: The omission of "%" in the list is to avoid double escaping!
    ESCAPE_CHARS = dict((ord(c), '%%%x'%ord(c)) for c in ' <>#"{}|\\^[]`')

    def __init__( self, channel):
        self.channel = channel
        self._auth_retry_counter = 0
        urllib.request.FancyURLopener.__init__(self, None)

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

    def redirect_internal(self, url, fp, errcode, errmsg, headers, data):
        """ This is the exact same function that's included with urllib
            except with "void = fp.read()" commented out. """

        if 'location' in headers:
            newurl = headers['location']
        elif 'uri' in headers:
            newurl = headers['uri']
        else:
            return

        # This blocks forever(?) with certain servers (see bug #465)
        #void = fp.read()
        fp.close()

        # In case the server sent a relative URL, join with original:
        newurl = urllib.parse.urljoin(self.type + ":" + url, newurl)
        return self.open(newurl)

# The following is based on Python's urllib.py "URLopener.retrieve"
# Also based on http://mail.python.org/pipermail/python-list/2001-October/110069.html

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        # The next line is taken from urllib's URLopener.open_http
        # method, at the end after the line "if errcode == 200:"
        return urllib.addinfourl(fp, headers, 'http:' + url)

    def retrieve_resume(self, url, filename, reporthook=None, data=None):
        """Download files from an URL; return (headers, real_url)

        Resumes a download if the local filename exists and
        the server supports download resuming.
        """

        current_size = 0
        tfp = None
        if os.path.exists(filename):
            try:
                current_size = os.path.getsize(filename)
                tfp = open(filename, 'ab')
                #If the file exists, then only download the remainder
                if current_size > 0:
                    self.addheader('Range', 'bytes=%s-' % (current_size))
            except:
                logger.warn('Cannot resume download: %s', filename, exc_info=True)
                tfp = None
                current_size = 0

        if tfp is None:
            tfp = open(filename, 'wb')

        # Fix a problem with bad URLs that are not encoded correctly (bug 549)
        url = url.translate(self.ESCAPE_CHARS)

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
                logger.warn('Cannot resume: Invalid Content-Range (RFC2616).')

        result = headers, fp.geturl()
        bs = 1024*8
        size = -1
        read = current_size
        blocknum = current_size//bs
        if reporthook:
            if "content-length" in headers:
                size = int(headers['Content-Length'])  + current_size
            reporthook(blocknum, bs, size)
        while read < size or size == -1:
            if size == -1:
                block = fp.read(bs)
            else:
                block = fp.read(min(size-read, bs))
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
            raise urllib.error.ContentTooShortError("retrieval incomplete: got only %i out "
                                       "of %i bytes" % (read, size), result)

        return result

# end code based on urllib.py

    def prompt_user_passwd( self, host, realm):
        # Keep track of authentication attempts, fail after the third one
        self._auth_retry_counter += 1
        if self._auth_retry_counter > 3:
            raise AuthenticationError(_('Wrong username/password'))

        if self.channel.auth_username or self.channel.auth_password:
            logger.debug('Authenticating as "%s" to "%s" for realm "%s".',
                    self.channel.auth_username, host, realm)
            return ( self.channel.auth_username, self.channel.auth_password )

        return (None, None)


class DownloadTask(Task):
    """An object representing the download task of an episode

    You can create a new download task like this:

        task = DownloadTask(episode, gpodder.config.Config(CONFIGFILE))
        task.status = Task.QUEUED
        task.run()

    The difference between cancelling and pausing a DownloadTask is
    that the temporary file gets deleted when cancelling, but does
    not get deleted when pausing.
    """
    # Possible states this download task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Downloading'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    ACTIVITY = DOWNLOAD_ACTIVITY

    def cleanup(self):
        util.delete_file(self.tempname)

    def __init__(self, episode, config):
        assert episode.download_task is None
        super(DownloadTask, self).__init__(DownloadTask.ACTIVITY, episode)
        self._config = config

        # Create the target filename and save it in the database
        self.filename = self.episode.local_filename(create=True)
        self.tempname = self.filename + '.partial'

        self.total_size = self.episode.file_size

        # Variables for speed limit and speed calculation
        self._speed_refresh_period = 5
        self.__limit_rate_value = self._config.limit_rate_value
        self.__limit_rate = self._config.limit_rate

        # If the tempname already exists, set progress accordingly
        if os.path.exists(self.tempname):
            try:
                already_downloaded = os.path.getsize(self.tempname)
                if self.total_size > 0:
                    self.progress = max(0.0, min(1.0, already_downloaded/self.total_size))
            except OSError as os_error:
                logger.error('Cannot get size for %s', os_error)
        else:
            # "touch self.tempname", so we also get partial
            # files for resuming when the file is queued
            open(self.tempname, 'w').close()

        # Store a reference to this task in the episode
        episode.download_task = self

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)
            if self.episode.file_size != self.total_size:
                logger.debug('Updating file size of %s to %s',
                        self.filename, self.total_size)
                self.episode.file_size = self.total_size
                self.episode.save()

        super(DownloadTask, self).status_updated(count, blockSize, totalSize)
        self.apply_speed_limit(count, blockSize)

    def apply_speed_limit(self, count, blockSize):
        if count % self._speed_refresh_period == 0:
            now = time.time()
            if self._start_time > 0:
                # Has rate limiting been enabled or disabled?
                if self.__limit_rate != self._config.limit_rate:
                    # If it has been enabled then reset base time and block count
                    if self._config.limit_rate:
                        self._start_time = now
                        self._start_blocks = count
                    self.__limit_rate = self._config.limit_rate

                # Has the rate been changed and are we currently limiting?
                if self.__limit_rate_value != self._config.limit_rate_value and self.__limit_rate:
                    self._start_time = now
                    self._start_blocks = count
                    self.__limit_rate_value = self._config.limit_rate_value

            limit_rate_value_bs = self.__limit_rate_value * 1024
            if self.__limit_rate and self.speed > limit_rate_value_bs:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                passed = now - self._start_time
                should_have_passed = (count - self._start_blocks) * blockSize / limit_rate_value_bs
                if should_have_passed > passed:
                    # sleep a maximum of 10 seconds to not cause time-outs
                    delay = min(10.0, float(should_have_passed-passed))
                    time.sleep(delay)

    def recycle(self):
        self.episode.download_task = None

    def do_run(self):
        try:
            # Resolve URL and start downloading the episode
            fmt_ids = youtube.get_fmt_ids(self._config.youtube)
            url = youtube.get_real_download_url(self.episode.url, fmt_ids)
            url = vimeo.get_real_download_url(url, self._config.vimeo.fileformat)
            url = escapist_videos.get_real_download_url(url)
            url = url.strip()

            # Properly escapes Unicode characters in the URL path section
            # TODO: Explore if this should also handle the domain
            # Based on: http://stackoverflow.com/a/18269491/1072626
            # In response to issue: https://github.com/gpodder/gpodder/issues/232
            def iri_to_url(url):
                url = urllib.parse.urlsplit(url)
                url = list(url)
                # First unquote to avoid escaping quoted content
                url[2] = urllib.parse.unquote(url[2])
                url[2] = urllib.parse.quote(url[2])
                url = urllib.parse.urlunsplit(url)
                return url

            url = iri_to_url(url)

            downloader = DownloadURLOpener(self.episode.channel)

            # HTTP Status codes for which we retry the download
            retry_codes = (408, 418, 504, 598, 599)
            max_retries = max(0, self._config.auto.retries)

            # Retry the download on timeout (bug 1013)
            for retry in range(max_retries + 1):
                if retry > 0:
                    logger.info('Retrying download of %s (%d)', url, retry)
                    time.sleep(1)

                try:
                    headers, real_url = downloader.retrieve_resume(url,
                        self.tempname, reporthook=self.status_updated)
                    # If we arrive here, the download was successful
                    break
                except urllib.error.ContentTooShortError as ctse:
                    if retry < max_retries:
                        logger.info('Content too short: %s - will retry.',
                                url)
                        continue
                    raise
                except socket.timeout as tmout:
                    if retry < max_retries:
                        logger.info('Socket timeout: %s - will retry.', url)
                        continue
                    raise
                except gPodderDownloadHTTPError as http:
                    if retry < max_retries and http.error_code in retry_codes:
                        logger.info('HTTP error %d: %s - will retry.',
                                http.error_code, url)
                        continue
                    raise

            new_mimetype = headers.get('content-type', self.episode.mime_type)
            old_mimetype = self.episode.mime_type
            _basename, ext = os.path.splitext(self.filename)
            if new_mimetype != old_mimetype or util.wrong_extension(ext):
                logger.info('Updating mime type: %s => %s', old_mimetype, new_mimetype)
                old_extension = self.episode.extension()
                self.episode.mime_type = new_mimetype
                new_extension = self.episode.extension()

                # If the desired filename extension changed due to the new
                # mimetype, we force an update of the local filename to fix the
                # extension.
                if old_extension != new_extension or util.wrong_extension(ext):
                    self.filename = self.episode.local_filename(create=True, force_update=True)

            # In some cases, the redirect of a URL causes the real filename to
            # be revealed in the final URL (e.g. http://gpodder.org/bug/1423)
            if real_url != url and not util.is_known_redirecter(real_url):
                realname, realext = util.filename_from_url(real_url)

                # Only update from redirect if the redirected-to filename has
                # a proper extension (this is needed for e.g. YouTube)
                if not util.wrong_extension(realext):
                    real_filename = ''.join((realname, realext))
                    self.filename = self.episode.local_filename(create=True,
                            force_update=True, template=real_filename)
                    logger.info('Download was redirected (%s). New filename: %s',
                            real_url, os.path.basename(self.filename))

            # Look at the Content-disposition header; use if if available
            disposition_filename = get_header_param(headers, 'filename', 'content-disposition')

            if disposition_filename is not None:
                try:
                    disposition_filename.decode('ascii')
                except:
                    logger.warn('Content-disposition header contains non-ASCII characters - ignoring')
                    disposition_filename = None

            # Some servers do send the content-disposition header, but provide
            # an empty filename, resulting in an empty string here (bug 1440)
            if disposition_filename is not None and disposition_filename != '':
                # The server specifies a download filename - try to use it
                disposition_filename = os.path.basename(disposition_filename)
                self.filename = self.episode.local_filename(create=True, \
                        force_update=True, template=disposition_filename)
                new_mimetype, encoding = mimetypes.guess_type(self.filename)
                if new_mimetype is not None:
                    logger.info('Using content-disposition mimetype: %s',
                            new_mimetype)
                    self.episode.mime_type = new_mimetype

            # Re-evaluate filename and tempname to take care of podcast renames
            # while downloads are running (which will change both file names)
            self.filename = self.episode.local_filename(create=False)
            self.tempname = os.path.join(os.path.dirname(self.filename),
                    os.path.basename(self.tempname))
            shutil.move(self.tempname, self.filename)

            # Model- and database-related updates after a download has finished
            self.episode.on_downloaded(self.filename)
        except TaskCancelledException:
            raise
        except urllib.error.ContentTooShortError as ctse:
            self.status = Task.FAILED
            self.error_message = _('Missing content from server')
        except IOError as ioe:
            logger.error('%s while downloading "%s": %s', ioe.strerror,
                    self.episode.title, ioe.filename, exc_info=True)
            self.status = Task.FAILED
            d = {'error': ioe.strerror, 'filename': ioe.filename}
            self.error_message = _('I/O Error: %(error)s: %(filename)s') % d
        except gPodderDownloadHTTPError as gdhe:
            logger.error('HTTP %s while downloading "%s": %s',
                    gdhe.error_code, self.episode.title, gdhe.error_message,
                    exc_info=True)
            self.status = Task.FAILED
            d = {'code': gdhe.error_code, 'message': gdhe.error_message}
            self.error_message = _('HTTP Error %(code)s: %(message)s') % d
        except Exception as e:
            self.status = Task.FAILED
            logger.error('Download failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        if self.status == Task.ACTIVE:
            # Everything went well - we're done
            self.status = Task.DONE
            if self.total_size <= 0:
                self.total_size = util.calculate_size(self.filename)
                logger.info('Total size updated to %d', self.total_size)
            self.progress = 1.0
            gpodder.user_extensions.on_episode_downloaded(self.episode)
            return True

        # We finished, but not successfully (at least not really)
        return False
