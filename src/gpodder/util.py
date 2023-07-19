# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
# Copyright (c) 2011 Neal H. Walfield
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
#  util.py -- Misc utility functions
#  Thomas Perl <thp@perli.net> 2007-08-04
#

"""Miscellaneous helper functions for gPodder

This module provides helper and utility functions for gPodder that
are not tied to any specific part of gPodder.

"""
import collections
import datetime
import email
import glob
import http.client
import itertools
import locale
import logging
import mimetypes
import os
import os.path
import platform
import re
import shlex
import shutil
import socket
import stat
import string
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import webbrowser
from html.entities import entitydefs, name2codepoint
from html.parser import HTMLParser

import requests
import requests.exceptions
from requests.packages.urllib3.util.retry import Retry

import gpodder

logger = logging.getLogger(__name__)


try:
    import html5lib
except ImportError:
    logger.warning("html5lib was not found, fall-back to HTMLParser")
    html5lib = None

if gpodder.ui.win32:
    try:
        import gpodder.utilwin32ctypes as win32file
    except ImportError:
        logger.warning('Running on Win32: utilwin32ctypes cannot be loaded')
        win32file = None

_ = gpodder.gettext
N_ = gpodder.ngettext


try:
    locale.setlocale(locale.LC_ALL, '')
except Exception as e:
    logger.warning('Cannot set locale (%s)', e, exc_info=True)

# Native filesystem encoding detection
encoding = sys.getfilesystemencoding()

if encoding is None:
    if 'LANG' in os.environ and '.' in os.environ['LANG']:
        lang = os.environ['LANG']
        (language, encoding) = lang.rsplit('.', 1)
        logger.info('Detected encoding: %s', encoding)
    elif gpodder.ui.win32:
        # To quote http://docs.python.org/howto/unicode.html:
        # ,,on Windows, Python uses the name "mbcs" to refer
        #   to whatever the currently configured encoding is``
        encoding = 'mbcs'
    else:
        encoding = 'iso-8859-15'
        logger.info('Assuming encoding: ISO-8859-15 ($LANG not set).')


# Filename / folder name sanitization
def _sanitize_char(c):
    if c in string.whitespace:
        return b' '
    elif c in ',-.()':
        return c.encode('utf-8')
    elif c in string.punctuation or ord(c) <= 31 or ord(c) >= 127:
        return b'_'

    return c.encode('utf-8')


SANITIZATION_TABLE = b''.join(map(_sanitize_char, list(map(chr, list(range(256))))))
del _sanitize_char

_MIME_TYPE_LIST = [
    ('.aac', 'audio/aac'),
    ('.axa', 'audio/annodex'),
    ('.flac', 'audio/flac'),
    ('.m4b', 'audio/m4b'),
    ('.m4a', 'audio/mp4'),
    ('.mp3', 'audio/mpeg'),
    ('.spx', 'audio/ogg'),
    ('.oga', 'audio/ogg'),
    ('.ogg', 'audio/ogg'),
    ('.wma', 'audio/x-ms-wma'),
    ('.3gp', 'video/3gpp'),
    ('.axv', 'video/annodex'),
    ('.divx', 'video/divx'),
    ('.m4v', 'video/m4v'),
    ('.mp4', 'video/mp4'),
    ('.ogv', 'video/ogg'),
    ('.mov', 'video/quicktime'),
    ('.flv', 'video/x-flv'),
    ('.mkv', 'video/x-matroska'),
    ('.wmv', 'video/x-ms-wmv'),
    ('.opus', 'audio/opus'),
    ('.webm', 'video/webm'),
    ('.webm', 'audio/webm'),
]

_MIME_TYPES = dict((k, v) for v, k in _MIME_TYPE_LIST)
_MIME_TYPES_EXT = dict(_MIME_TYPE_LIST)


def is_absolute_url(url):
    """
    Check if url is an absolute url (i.e. has a scheme)
    """
    try:
        parsed = urllib.parse.urlparse(url)
        # fix #1190: when parsing a windows path, scheme=drive_letter, path=\rest_of_path
        return parsed.scheme and not parsed.path.startswith("\\")
    except ValueError:
        return False


def new_gio_file(path):
    """
    Create a new Gio.File given a path or uri
    """
    from gi.repository import Gio

    if is_absolute_url(path):
        return Gio.File.new_for_uri(path)
    else:
        return Gio.File.new_for_path(path)


def make_directory(path):
    """
    Tries to create a directory if it does not exist already.
    Returns True if the directory exists after the function
    call, False otherwise.
    """
    from gi.repository import Gio, GLib

    if not isinstance(path, Gio.File):
        path = new_gio_file(path)

    if path.query_exists():
        return True

    try:
        path.make_directory_with_parents()
    except GLib.Error as err:
        # The sync might be multithreaded, so directories can be created by other threads
        if not err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.EXISTS):
            logger.warning('Could not create directory %s: %s', path.get_uri(), err.message)
            return False

    return True


def normalize_feed_url(url):
    """
    Converts any URL to http:// or ftp:// so that it can be
    used with "wget". If the URL cannot be converted (invalid
    or unknown scheme), "None" is returned.

    This will also normalize feed:// and itpc:// to http://.

    >>> normalize_feed_url('itpc://example.org/podcast.rss')
    'http://example.org/podcast.rss'

    If no URL scheme is defined (e.g. "curry.com"), we will
    simply assume the user intends to add a http:// feed.

    >>> normalize_feed_url('curry.com')
    'http://curry.com/'

    There are even some more shortcuts for advanced users
    and lazy typists (see the source for details).

    >>> normalize_feed_url('fb:43FPodcast')
    'http://feeds.feedburner.com/43FPodcast'

    It will also take care of converting the domain name to
    all-lowercase (because domains are not case sensitive):

    >>> normalize_feed_url('http://Example.COM/')
    'http://example.com/'

    Some other minimalistic changes are also taken care of,
    e.g. a ? with an empty query is removed:

    >>> normalize_feed_url('http://example.org/test?')
    'http://example.org/test'

    Username and password in the URL must not be affected
    by URL normalization (see gPodder bug 1942):

    >>> normalize_feed_url('http://UserName:PassWord@Example.com/')
    'http://UserName:PassWord@example.com/'
    """
    if not url or len(url) < 8:
        return None

    # Removes leading and/or trailing whitespaces - if url contains whitespaces
    # in between after str.strip() -> conclude invalid url & return None
    url = url.strip()
    if ' ' in url:
        return None

    # This is a list of prefixes that you can use to minimize the amount of
    # keystrokes that you have to use.
    # Feel free to suggest other useful prefixes, and I'll add them here.
    PREFIXES = {
            'fb:': 'http://feeds.feedburner.com/%s',
            'yt:': 'http://www.youtube.com/rss/user/%s/videos.rss',
            'sc:': 'https://soundcloud.com/%s',
            # YouTube playlists. To get a list of playlists per-user, use:
            # https://gdata.youtube.com/feeds/api/users/<username>/playlists
            'ytpl:': 'http://gdata.youtube.com/feeds/api/playlists/%s',
    }

    for prefix, expansion in PREFIXES.items():
        if url.startswith(prefix):
            url = expansion % (url[len(prefix):],)
            break

    # Assume HTTP for URLs without scheme
    if '://' not in url:
        url = 'http://' + url

    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)

    # Domain name is case insensitive, but username/password is not (bug 1942)
    if '@' in netloc:
        authentication, netloc = netloc.rsplit('@', 1)
        netloc = '@'.join((authentication, netloc.lower()))
    else:
        netloc = netloc.lower()

    # Schemes and domain names are case insensitive
    scheme = scheme.lower()

    # Normalize empty paths to "/"
    if path == '':
        path = '/'

    # feed://, itpc:// and itms:// are really http://
    if scheme in ('feed', 'itpc', 'itms'):
        scheme = 'http'

    if scheme not in ('http', 'https', 'ftp', 'file'):
        return None

    # urlunsplit might return "a slightly different, but equivalent URL"
    return urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))


def username_password_from_url(url):
    r"""
    Returns a tuple (username,password) containing authentication
    data from the specified URL or (None,None) if no authentication
    data can be found in the URL.

    See Section 3.1 of RFC 1738 (http://www.ietf.org/rfc/rfc1738.txt)

    >>> username_password_from_url('https://@host.com/')
    ('', None)
    >>> username_password_from_url('telnet://host.com/')
    (None, None)
    >>> username_password_from_url('ftp://foo:@host.com/')
    ('foo', '')
    >>> username_password_from_url('http://a:b@host.com/')
    ('a', 'b')
    >>> username_password_from_url(1)
    Traceback (most recent call last):
      ...
    ValueError: URL has to be a string.
    >>> username_password_from_url(None)
    Traceback (most recent call last):
      ...
    ValueError: URL has to be a string.
    >>> username_password_from_url('http://a@b:c@host.com/')
    ('a@b', 'c')
    >>> username_password_from_url('ftp://a:b:c@host.com/')
    ('a', 'b:c')
    >>> username_password_from_url('http://i%2Fo:P%40ss%3A@host.com/')
    ('i/o', 'P@ss:')
    >>> username_password_from_url('ftp://%C3%B6sterreich@host.com/')
    ('österreich', None)
    >>> username_password_from_url('http://w%20x:y%20z@example.org/')
    ('w x', 'y z')
    >>> username_password_from_url('http://example.com/x@y:z@test.com/')
    (None, None)
    """
    if not isinstance(url, str):
        raise ValueError('URL has to be a string.')

    (username, password) = (None, None)

    (scheme, netloc, path, params, query, fragment) = urllib.parse.urlparse(url)

    if '@' in netloc:
        (authentication, netloc) = netloc.rsplit('@', 1)
        if ':' in authentication:
            (username, password) = authentication.split(':', 1)

            # RFC1738 dictates that we should not allow ['/', '@', ':']
            # characters in the username and password field (Section 3.1):
            #
            # 1. The "/" can't be in there at this point because of the way
            #    urlparse (which we use above) works.
            # 2. Due to gPodder bug 1521, we allow "@" in the username and
            #    password field. We use netloc.rsplit('@', 1), which will
            #    make sure that we split it at the last '@' in netloc.
            # 3. The colon must be excluded (RFC2617, Section 2) in the
            #    username, but is apparently allowed in the password. This
            #    is handled by the authentication.split(':', 1) above, and
            #    will cause any extraneous ':'s to be part of the password.

            username = urllib.parse.unquote(username)
            password = urllib.parse.unquote(password)
        else:
            username = urllib.parse.unquote(authentication)

    return (username, password)


def directory_is_writable(path):
    """
    Returns True if the specified directory exists and is writable
    by the current user.
    """
    return os.path.isdir(path) and os.access(path, os.W_OK)


def calculate_size(path):
    """
    Tries to calculate the size of a directory, including any
    subdirectories found. The returned value might not be
    correct if the user doesn't have appropriate permissions
    to list all subdirectories of the given path.
    """
    if path is None:
        return 0

    if os.path.dirname(path) == '/':
        return 0

    if os.path.isfile(path):
        return os.path.getsize(path)

    if os.path.isdir(path) and not os.path.islink(path):
        sum = os.path.getsize(path)

        try:
            for item in os.listdir(path):
                try:
                    sum += calculate_size(os.path.join(path, item))
                except:
                    logger.warning('Cannot get size for %s', path, exc_info=True)
        except:
            logger.warning('Cannot access %s', path, exc_info=True)

        return sum

    return 0


def file_modification_datetime(filename):
    """
    Returns the modification date of the specified file
    as a datetime.datetime object or None if the modification
    date cannot be determined.
    """
    if filename is None:
        return None

    if not os.access(filename, os.R_OK):
        return None

    try:
        s = os.stat(filename)
        timestamp = s[stat.ST_MTIME]
        return datetime.datetime.fromtimestamp(timestamp)
    except:
        logger.warning('Cannot get mtime for %s', filename, exc_info=True)
        return None


def file_age_in_days(filename):
    """
    Returns the age of the specified filename in days or
    zero if the modification date cannot be determined.
    """
    dt = file_modification_datetime(filename)
    if dt is None:
        return 0
    else:
        return (datetime.datetime.now() - dt).days


def file_modification_timestamp(filename):
    """
    Returns the modification date of the specified file as a number
    or -1 if the modification date cannot be determined.
    """
    if filename is None:
        return -1
    try:
        s = os.stat(filename)
        return s[stat.ST_MTIME]
    except:
        logger.warning('Cannot get modification timestamp for %s', filename)
        return -1


def file_age_to_string(days):
    """
    Converts a "number of days" value to a string that
    can be used in the UI to display the file age.

    >>> file_age_to_string(0)
    ''
    >>> file_age_to_string(1)
    '1 day ago'
    >>> file_age_to_string(2)
    '2 days ago'
    """
    if days < 1:
        return ''
    else:
        return N_('%(count)d day ago', '%(count)d days ago', days) % {'count': days}


def is_system_file(filename):
    """
    Checks to see if the given file is a system file.
    """
    if gpodder.ui.win32 and win32file is not None:
        result = win32file.GetFileAttributes(filename)
        # -1 / 0xffffffff is returned by GetFileAttributes when an error occurs
        # 0x4 is the FILE_ATTRIBUTE_SYSTEM constant
        return result != -1 and result != 0xffffffff and result & 0x4 != 0
    else:
        return False


def get_free_disk_space_win32(path):
    """
    Win32-specific code to determine the free disk space remaining
    for a given path. Uses code from:

    http://mail.python.org/pipermail/python-list/2003-May/203223.html
    """
    if win32file is None:
        # Cannot determine free disk space
        return -1

    drive, tail = os.path.splitdrive(path)
    userFree, userTotal, freeOnDisk = win32file.GetDiskFreeSpaceEx(drive)
    return userFree


def get_free_disk_space(path):
    """
    Calculates the free disk space available to the current user
    on the file system that contains the given path.

    If the path (or its parent folder) does not yet exist, this
    function returns zero.
    """

    if not os.path.exists(path):
        return -1

    if gpodder.ui.win32:
        return get_free_disk_space_win32(path)

    s = os.statvfs(path)

    return s.f_bavail * s.f_bsize


def format_date(timestamp):
    """
    Converts a UNIX timestamp to a date representation. This
    function returns "Today", "Yesterday", a weekday name or
    the date in %x format, which (according to the Python docs)
    is the "Locale's appropriate date representation".

    Returns None if there has been an error converting the
    timestamp to a string representation.
    """
    if timestamp is None:
        return None

    seconds_in_a_day = 60 * 60 * 24

    today = time.localtime()[:3]
    yesterday = time.localtime(time.time() - seconds_in_a_day)[:3]
    try:
        timestamp_date = time.localtime(timestamp)[:3]
    except ValueError as e:
        logger.warning('Cannot convert timestamp', exc_info=True)
        return None
    except TypeError as e:
        logger.warning('Cannot convert timestamp', exc_info=True)
        return None

    if timestamp_date == today:
        return _('Today')
    elif timestamp_date == yesterday:
        return _('Yesterday')

    try:
        diff = int((time.time() - timestamp) / seconds_in_a_day)
    except:
        logger.warning('Cannot convert "%s" to date.', timestamp, exc_info=True)
        return None

    try:
        timestamp = datetime.datetime.fromtimestamp(timestamp)
    except:
        return None

    if diff < 7:
        # Weekday name
        return timestamp.strftime('%A')
    else:
        # Locale's appropriate date representation
        return timestamp.strftime('%x')


def format_filesize(bytesize, use_si_units=False, digits=2):
    """
    Formats the given size in bytes to be human-readable,

    Returns a localized "(unknown)" string when the bytesize
    has a negative value.
    """
    si_units = (
            ('kB', 10**3),
            ('MB', 10**6),
            ('GB', 10**9),
    )

    binary_units = (
            ('KiB', 2**10),
            ('MiB', 2**20),
            ('GiB', 2**30),
    )

    try:
        bytesize = float(bytesize)
    except:
        return _('(unknown)')

    if bytesize < 0:
        return _('(unknown)')

    if use_si_units:
        units = si_units
    else:
        units = binary_units

    (used_unit, used_value) = ('B', bytesize)

    for (unit, value) in units:
        if bytesize >= value:
            used_value = bytesize / float(value)
            used_unit = unit

    return locale.format_string('%.' + str(digits) + 'f\u00a0%s', (used_value, used_unit))


def delete_file(filename):
    """Delete a file from the filesystem

    Errors (permissions errors or file not found)
    are silently ignored.
    """
    try:
        os.remove(filename)
    except:
        pass


def is_html(text):
    """Heuristically tell if text is HTML

    By looking for an open tag (more or less:)
    >>> is_html('<h1>HELLO</h1>')
    True
    >>> is_html('a < b < c')
    False
    """
    html_test = re.compile(r'<[a-z][a-z0-9]*(?:\s.*?>|\/?>)', re.IGNORECASE | re.DOTALL)
    return bool(html_test.search(text))


def remove_html_tags(html):
    """
    Remove HTML tags from a string and replace numeric and
    named entities with the corresponding character, so the
    HTML text can be displayed in a simple text view.
    """
    if html is None:
        return None

    # If we would want more speed, we could make these global
    re_strip_tags = re.compile(r'<[^>]*>')
    re_unicode_entities = re.compile(r'&#(\d{2,4});')
    re_html_entities = re.compile(r'&(.{2,8});')
    re_newline_tags = re.compile(r'(<br[^>]*>|<[/]?ul[^>]*>|</li>)', re.I)
    re_listing_tags = re.compile(r'<li[^>]*>', re.I)

    result = html

    # Convert common HTML elements to their text equivalent
    result = re_newline_tags.sub('\n', result)
    result = re_listing_tags.sub('\n * ', result)
    result = re.sub(r'<[Pp]>', '\n\n', result)

    # Remove all HTML/XML tags from the string
    result = re_strip_tags.sub('', result)

    # Convert numeric XML entities to their unicode character
    result = re_unicode_entities.sub(lambda x: chr(int(x.group(1))), result)

    # Convert named HTML entities to their unicode character
    result = re_html_entities.sub(lambda x: entitydefs.get(x.group(1), ''), result)

    # Convert more than two newlines to two newlines
    result = re.sub(r'([\r\n]{2})([\r\n])+', '\\1', result)

    return result.strip()


class HyperlinkExtractor(object):
    def __init__(self):
        self.parts = []
        self.target_stack = [None]
        self.ignore_data = False

    def get_result(self):
        # Group together multiple consecutive parts with same link target,
        # and remove excessive newlines.
        group_it = itertools.groupby(self.parts, key=lambda x: x[0])
        result = []
        for target, parts in group_it:
            t = ''.join(text for _, text in parts if text is not None)
            # Remove trailing spaces
            t = re.sub(r' +\n', '\n', t)
            # Convert more than two newlines to two newlines
            t = t.replace('\r', '')
            t = re.sub(r'\n\n\n+', '\n\n', t)
            result.append((target, t))
        # Strip leading and trailing whitespace
        result[0] = (result[0][0], result[0][1].lstrip())
        result[-1] = (result[-1][0], result[-1][1].rstrip())
        return result

    def htmlws(self, s):
        # Replace whitespaces with a single space per HTML spec.
        if s is not None:
            return re.sub(r'[ \t\n\r]+', ' ', s)

    def handle_starttag(self, tag_name, attrs):
        try:
            handler = getattr(self, 'handle_start_' + tag_name)
        except AttributeError:
            pass
        else:
            handler(collections.OrderedDict(attrs))

    def handle_endtag(self, tag_name):
        try:
            handler = getattr(self, 'handle_end_' + tag_name)
        except AttributeError:
            pass
        else:
            handler()

    def handle_start_a(self, attrs):
        self.target_stack.append(attrs.get('href'))

    def handle_end_a(self):
        if len(self.target_stack) > 1:
            self.target_stack.pop()

    def handle_start_style(self, attrs):
        self.ignore_data = True

    def handle_end_style(self):
        self.ignore_data = False

    def output(self, text):
        self.parts.append((self.target_stack[-1], text))

    def handle_data(self, data):
        if not self.ignore_data:
            self.output(self.htmlws(data))

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        self.output(c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        self.output(c)

    def output_newline(self, attrs=None):
        self.output('\n')

    def output_double_newline(self, attrs=None):
        self.output('\n')

    def handle_start_img(self, attrs):
        self.output(self.htmlws(attrs.get('alt', '')))

    def handle_start_li(self, attrs):
        self.output('\n * ')

    handle_end_li = handle_end_ul = handle_start_br = output_newline
    handle_start_p = handle_end_p = output_double_newline


class ExtractHyperlinkedText(object):
    def __call__(self, document):
        self.extractor = HyperlinkExtractor()
        self.visit(document)
        return self.extractor.get_result()

    def visit(self, element):
        # skip functions generated by html5lib for comments in the HTML
        if callable(element.tag):
            return

        NS = '{http://www.w3.org/1999/xhtml}'
        tag_name = (element.tag[len(NS):] if element.tag.startswith(NS) else element.tag).lower()
        self.extractor.handle_starttag(tag_name, list(element.items()))

        if element.text is not None:
            self.extractor.handle_data(element.text)

        for child in element:
            self.visit(child)

            if child.tail is not None:
                self.extractor.handle_data(child.tail)

        self.extractor.handle_endtag(tag_name)


class ExtractHyperlinkedTextHTMLParser(HTMLParser):
    def __call__(self, html):
        self.extractor = HyperlinkExtractor()
        self.target_stack = [None]
        self.feed(html)
        self.close()
        return self.extractor.get_result()

    def handle_starttag(self, tag, attrs):
        self.extractor.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.extractor.handle_endtag(tag)

    def handle_data(self, data):
        self.extractor.handle_data(data)

    def handle_entityref(self, name):
        self.extractor.handle_entityref(name)

    def handle_charref(self, name):
        self.extractor.handle_charref(name)


def extract_hyperlinked_text(html):
    """
    Convert HTML to hyperlinked text.

    The output is a list of (target, text) tuples, where target is either a URL
    or None, and text is a piece of plain text for rendering in a TextView.
    """
    if '<' not in html:
        # Probably plain text. We would remove all the newlines
        # if we treated it as HTML, so just pass it back as-is.
        return [(None, html)]

    if html5lib is not None:
        return ExtractHyperlinkedText()(html5lib.parseFragment(html))
    else:
        return ExtractHyperlinkedTextHTMLParser()(html)


def nice_html_description(img, description):
    """
    basic html formatting + hyperlink highlighting + video thumbnail
    """
    description = re.sub(r'''https?://[^\s]+''',
                         r'''<a href="\g<0>">\g<0></a>''',
                         description)
    description = description.replace('\n', '<br>')
    html = """<style type="text/css">
    body > img { float: left; max-width: 30vw; margin: 0 1em 1em 0; }
    </style>
    """
    if img:
        html += '<img src="{}">'.format(img)
    html += '<p>{}</p>'.format(description)
    return html


def wrong_extension(extension):
    """
    Determine if a given extension looks like it's
    wrong (e.g. empty, extremely long or spaces)

    Returns True if the extension most likely is a
    wrong one and should be replaced.

    >>> wrong_extension('.mp3')
    False
    >>> wrong_extension('.divx')
    False
    >>> wrong_extension('mp3')
    True
    >>> wrong_extension('')
    True
    >>> wrong_extension('.12 - Everybody')
    True
    >>> wrong_extension('.mp3 ')
    True
    >>> wrong_extension('.')
    True
    >>> wrong_extension('.42')
    True
    """
    if not extension:
        return True
    elif len(extension) > 5:
        return True
    elif ' ' in extension:
        return True
    elif extension == '.':
        return True
    elif not extension.startswith('.'):
        return True
    else:
        try:
            # ".<number>" is an invalid extension
            float(extension)
            return True
        except:
            pass

    return False


def extension_from_mimetype(mimetype):
    """
    Simply guesses what the file extension should be from the mimetype

    >>> extension_from_mimetype('audio/mp4')
    '.m4a'
    >>> extension_from_mimetype('audio/ogg')
    '.ogg'
    >>> extension_from_mimetype('audio/mpeg')
    '.mp3'
    >>> extension_from_mimetype('video/x-matroska')
    '.mkv'
    >>> extension_from_mimetype('wrong-mimetype')
    ''
    """
    if mimetype in _MIME_TYPES:
        return _MIME_TYPES[mimetype]
    return mimetypes.guess_extension(mimetype) or ''


def mimetype_from_extension(extension):
    """
    Simply guesses what the mimetype should be from the file extension

    >>> mimetype_from_extension('.m4a')
    'audio/mp4'
    >>> mimetype_from_extension('.ogg')
    'audio/ogg'
    >>> mimetype_from_extension('.mp3')
    'audio/mpeg'
    >>> mimetype_from_extension('.mkv')
    'video/x-matroska'
    >>> mimetype_from_extension('._invalid_file_extension_')
    ''
    """
    if extension in _MIME_TYPES_EXT:
        return _MIME_TYPES_EXT[extension]

    # Need to prepend something to the extension, so guess_type works
    type, encoding = mimetypes.guess_type('file' + extension)

    return type or ''


def extension_correct_for_mimetype(extension, mimetype):
    """
    Check if the given filename extension (e.g. ".ogg") is a possible
    extension for a given mimetype (e.g. "application/ogg") and return
    a boolean value (True if it's possible, False if not). Also do

    >>> extension_correct_for_mimetype('.ogg', 'application/ogg')
    True
    >>> extension_correct_for_mimetype('.ogv', 'video/ogg')
    True
    >>> extension_correct_for_mimetype('.ogg', 'audio/mpeg')
    False
    >>> extension_correct_for_mimetype('.m4a', 'audio/mp4')
    True
    >>> extension_correct_for_mimetype('mp3', 'audio/mpeg')
    Traceback (most recent call last):
      ...
    ValueError: "mp3" is not an extension (missing .)
    >>> extension_correct_for_mimetype('.mp3', 'audio mpeg')
    Traceback (most recent call last):
      ...
    ValueError: "audio mpeg" is not a mimetype (missing /)
    """
    if '/' not in mimetype:
        raise ValueError('"%s" is not a mimetype (missing /)' % mimetype)
    if not extension.startswith('.'):
        raise ValueError('"%s" is not an extension (missing .)' % extension)

    if (extension, mimetype) in _MIME_TYPE_LIST:
        return True

    # Create a "default" extension from the mimetype, e.g. "application/ogg"
    # becomes ".ogg", "audio/mpeg" becomes ".mpeg", etc...
    default = ['.' + mimetype.split('/')[-1]]

    return extension in default + mimetypes.guess_all_extensions(mimetype)


def filename_from_url(url):
    """
    Extracts the filename and (lowercase) extension (with dot)
    from a URL, e.g. http://server.com/file.MP3?download=yes
    will result in the string ("file", ".mp3") being returned.

    This function will also try to best-guess the "real"
    extension for a media file (audio, video) by
    trying to match an extension to these types and recurse
    into the query string to find better matches, if the
    original extension does not resolve to a known type.

    http://my.net/redirect.php?my.net/file.ogg => ("file", ".ogg")
    http://server/get.jsp?file=/episode0815.MOV => ("episode0815", ".mov")
    http://s/redirect.mp4?http://serv2/test.mp4 => ("test", ".mp4")
    """
    (scheme, netloc, path, params, query, fragment) = urllib.parse.urlparse(url)
    (filename, extension) = os.path.splitext(
        os.path.basename(urllib.parse.unquote(path)))

    if file_type_by_extension(extension) is not None and not \
            query.startswith(scheme + '://'):
        # We have found a valid extension (audio, video)
        # and the query string doesn't look like a URL
        return (filename, extension.lower())

    # If the query string looks like a possible URL, try that first
    if len(query.strip()) > 0 and query.find('/') != -1:
        query_url = '://'.join((scheme, urllib.parse.unquote(query)))
        (query_filename, query_extension) = filename_from_url(query_url)

        if file_type_by_extension(query_extension) is not None:
            return os.path.splitext(os.path.basename(query_url))

    # No exact match found, simply return the original filename & extension
    return (filename, extension.lower())


def file_type_by_extension(extension):
    """
    Tries to guess the file type by looking up the filename
    extension from a table of known file types. Will return
    "audio", "video" or None.

    >>> file_type_by_extension('.aif')
    'audio'
    >>> file_type_by_extension('.3GP')
    'video'
    >>> file_type_by_extension('.m4a')
    'audio'
    >>> file_type_by_extension('.txt') is None
    True
    >>> file_type_by_extension(None) is None
    True
    >>> file_type_by_extension('ogg')
    Traceback (most recent call last):
      ...
    ValueError: Extension does not start with a dot: ogg
    """
    if not extension:
        return None

    if not extension.startswith('.'):
        raise ValueError('Extension does not start with a dot: %s' % extension)

    extension = extension.lower()

    if extension in _MIME_TYPES_EXT:
        return _MIME_TYPES_EXT[extension].split('/')[0]

    # Need to prepend something to the extension, so guess_type works
    type, encoding = mimetypes.guess_type('file' + extension)

    if type is not None and '/' in type:
        filetype, rest = type.split('/', 1)
        if filetype in ('audio', 'video', 'image'):
            return filetype

    return None


def get_first_line(s):
    """
    Returns only the first line of a string, stripped so
    that it doesn't have whitespace before or after.
    """
    if s:
        return s.strip().split('\n')[0].strip()
    return ''


def object_string_formatter(s, **kwargs):
    """
    Makes attributes of object passed in as keyword
    arguments available as {OBJECTNAME.ATTRNAME} in
    the passed-in string and returns a string with
    the above arguments replaced with the attribute
    values of the corresponding object.

    >>> class x: pass
    >>> a = x()
    >>> a.title = 'Hello world'
    >>> object_string_formatter('{episode.title}', episode=a)
    'Hello world'

    >>> class x: pass
    >>> a = x()
    >>> a.published = 123
    >>> object_string_formatter('Hi {episode.published} 456', episode=a)
    'Hi 123 456'
    """
    result = s
    for key, o in kwargs.items():
        matches = re.findall(r'\{%s\.([^\}]+)\}' % key, s)
        for attr in matches:
            if hasattr(o, attr):
                try:
                    from_s = '{%s.%s}' % (key, attr)
                    to_s = str(getattr(o, attr))
                    result = result.replace(from_s, to_s)
                except:
                    logger.warning('Replace of "%s" failed for "%s".', attr, s)

    return result


def format_desktop_command(command, filenames, start_position=None):
    """
    Formats a command template from the "Exec=" line of a .desktop
    file to a string that can be invoked in a shell.

    Handled format strings: %U, %u, %F, %f and a fallback that
    appends the filename as first parameter of the command.

    Also handles non-standard %p which is replaced with the start_position
    (probably only makes sense if starting a single file). (see bug 1140)

    See http://standards.freedesktop.org/desktop-entry-spec/1.0/ar01s06.html

    Returns a list of commands to execute, either one for
    each filename if the application does not support multiple
    file names or one for all filenames (%U, %F or unknown).
    """
    # Replace backslashes with slashes to fix win32 issues
    # (even on win32, "/" works, but "\" does not)
    command = command.replace('\\', '/')

    if start_position is not None:
        command = command.replace('%p', str(start_position))

    command = shlex.split(command)

    command_before = command
    command_after = []
    multiple_arguments = True
    for fieldcode in ('%U', '%F', '%u', '%f'):
        if fieldcode in command:
            command_before = command[:command.index(fieldcode)]
            command_after = command[command.index(fieldcode) + 1:]
            multiple_arguments = fieldcode in ('%U', '%F')
            break

    if multiple_arguments:
        return [command_before + filenames + command_after]

    commands = []
    for filename in filenames:
        commands.append(command_before + [filename] + command_after)

    return commands


def url_strip_authentication(url):
    """
    Strips authentication data from an URL. Returns the URL with
    the authentication data removed from it.

    >>> url_strip_authentication('https://host.com/')
    'https://host.com/'
    >>> url_strip_authentication('telnet://foo:bar@host.com/')
    'telnet://host.com/'
    >>> url_strip_authentication('ftp://billy@example.org')
    'ftp://example.org'
    >>> url_strip_authentication('ftp://billy:@example.org')
    'ftp://example.org'
    >>> url_strip_authentication('http://aa:bc@localhost/x')
    'http://localhost/x'
    >>> url_strip_authentication('http://i%2Fo:P%40ss%3A@blubb.lan/u.html')
    'http://blubb.lan/u.html'
    >>> url_strip_authentication('http://c:d@x.org/')
    'http://x.org/'
    >>> url_strip_authentication('http://P%40%3A:i%2F@cx.lan')
    'http://cx.lan'
    >>> url_strip_authentication('http://x@x.com:s3cret@example.com/')
    'http://example.com/'
    """
    url_parts = list(urllib.parse.urlsplit(url))
    # url_parts[1] is the HOST part of the URL

    # Remove existing authentication data
    if '@' in url_parts[1]:
        url_parts[1] = url_parts[1].rsplit('@', 1)[1]

    return urllib.parse.urlunsplit(url_parts)


def url_add_authentication(url, username, password):
    """
    Adds authentication data (username, password) to a given
    URL in order to construct an authenticated URL.

    >>> url_add_authentication('https://host.com/', '', None)
    'https://host.com/'
    >>> url_add_authentication('http://example.org/', None, None)
    'http://example.org/'
    >>> url_add_authentication('telnet://host.com/', 'foo', 'bar')
    'telnet://foo:bar@host.com/'
    >>> url_add_authentication('ftp://example.org', 'billy', None)
    'ftp://billy@example.org'
    >>> url_add_authentication('ftp://example.org', 'billy', '')
    'ftp://billy:@example.org'
    >>> url_add_authentication('http://localhost/x', 'aa', 'bc')
    'http://aa:bc@localhost/x'
    >>> url_add_authentication('http://blubb.lan/u.html', 'i/o', 'P@ss:')
    'http://i%2Fo:P@ss:@blubb.lan/u.html'
    >>> url_add_authentication('http://a:b@x.org/', 'c', 'd')
    'http://c:d@x.org/'
    >>> url_add_authentication('http://i%2F:P%40%3A@cx.lan', 'P@x', 'i/')
    'http://P@x:i%2F@cx.lan'
    >>> url_add_authentication('http://x.org/', 'a b', 'c d')
    'http://a%20b:c%20d@x.org/'
    """
    if username is None or username == '':
        return url

    # Relaxations of the strict quoting rules (bug 1521):
    # 1. Accept '@' in username and password
    # 2. Acecpt ':' in password only
    username = urllib.parse.quote(username, safe='@')

    if password is not None:
        password = urllib.parse.quote(password, safe='@:')
        auth_string = ':'.join((username, password))
    else:
        auth_string = username

    url = url_strip_authentication(url)

    url_parts = list(urllib.parse.urlsplit(url))
    # url_parts[1] is the HOST part of the URL
    url_parts[1] = '@'.join((auth_string, url_parts[1]))

    return urllib.parse.urlunsplit(url_parts)


def urlopen(url, headers=None, data=None, timeout=None, **kwargs):
    """
    An URL opener with the User-agent set to gPodder (with version)
    """
    if headers is None:
        headers = {}
    else:
        headers = dict(headers)

    if not timeout:
        timeout = gpodder.SOCKET_TIMEOUT

    retry_strategy = Retry(
        total=3,
        status_forcelist=Retry.RETRY_AFTER_STATUS_CODES.union((408, 418, 504, 598, 599,)))
    s = requests.Session()
    a = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    s.mount('http://', a)
    s.mount('https://', a)
    headers.update({'User-agent': gpodder.user_agent})
    return s.get(url, headers=headers, data=data, timeout=timeout, **kwargs)


def get_real_url(url):
    """
    Gets the real URL of a file and resolves all redirects.
    """
    try:
        return urlopen(url).url
    except:
        logger.error('Getting real url for %s', url, exc_info=True)
        return url


def find_command(command):
    """
    Searches the system's PATH for a specific command that is
    executable by the user. Returns the first occurrence of an
    executable binary in the PATH, or None if the command is
    not available.

    On Windows, this also looks for "<command>.bat" and
    "<command>.exe" files if "<command>" itself doesn't exist.
    """

    if 'PATH' not in os.environ:
        return None

    for path in os.environ['PATH'].split(os.pathsep):
        command_file = os.path.join(path, command)
        if gpodder.ui.win32 and not os.path.exists(command_file):
            for extension in ('.bat', '.exe'):
                cmd = command_file + extension
                if os.path.isfile(cmd):
                    command_file = cmd
                    break
        if os.path.isfile(command_file) and os.access(command_file, os.X_OK):
            return command_file

    return None


def idle_add(func, *args):
    """Run a function in the main GUI thread

    This is a wrapper function that does the Right Thing depending on if we are
    running on Gtk+, Qt or CLI.

    You should use this function if you are calling from a Python thread and
    modify UI data, so that you make sure that the function is called as soon
    as possible from the main UI thread.
    """
    if gpodder.ui.gtk:
        from gi.repository import GLib
        GLib.idle_add(func, *args)
    else:
        func(*args)


def idle_timeout_add(milliseconds, func, *args):
    """Run a function in the main GUI thread at regular intervals, at idle priority

    PRIORITY_HIGH           -100
    PRIORITY_DEFAULT        0        timeout_add()
    PRIORITY_HIGH_IDLE      100
    resizing                110
    redraw                  120
    PRIORITY_DEFAULT_IDLE   200      idle_add()
    PRIORITY_LOW            300
    """
    if not gpodder.ui.gtk:
        raise Exception('util.idle_timeout_add() is only supported by Gtk+')
    from gi.repository import GLib
    return GLib.timeout_add(milliseconds, func, *args, priority=GLib.PRIORITY_DEFAULT_IDLE)


class IdleTimeout(object):
    """Run a function in the main GUI thread at regular intervals since the last run, at idle priority

    A simple timeout_add() continuously calls the function if it exceeds the interval,
    which lags the UI and prevents idle_add() calls from happening. This class restarts
    the timer after the function finishes, allowing other callbacks to run.
    """
    def __init__(self, milliseconds, func, *args):
        if not gpodder.ui.gtk:
            raise Exception('util.IdleTimeout() is only supported by Gtk+')
        self.milliseconds = milliseconds
        self.max_milliseconds = 0
        self.func = func
        from gi.repository import GLib
        self.id = GLib.timeout_add(milliseconds, self._callback, *args, priority=GLib.PRIORITY_DEFAULT_IDLE)

    def set_max_milliseconds(self, max):
        self.max_milliseconds = max
        return self

    def _callback(self, *args):
        self.cancel()
        start_time = time.time()
        if self.func(*args):
            if self.max_milliseconds > self.milliseconds:
                duration = round((time.time() - start_time) * 1000)
                if duration > self.max_milliseconds:
                    duration = self.max_milliseconds
                milliseconds = round(lerp(self.milliseconds, self.max_milliseconds, duration / self.max_milliseconds))
            else:
                milliseconds = self.milliseconds
            from gi.repository import GLib
            self.id = GLib.timeout_add(milliseconds, self._callback, *args, priority=GLib.PRIORITY_DEFAULT_IDLE)

    def cancel(self):
        if self.id:
            from gi.repository import GLib
            GLib.source_remove(self.id)
            self.id = 0


def lerp(a, b, f):
    """Linear interpolation between 'a' and 'b', where 'f' is between 0.0 and 1.0
    """
    return ((1.0 - f) * a) + (f * b)


def bluetooth_available():
    """
    Returns True or False depending on the availability
    of bluetooth functionality on the system.
    """
    if find_command('bluetooth-sendto') or \
            find_command('gnome-obex-send'):
        return True
    else:
        return False


def bluetooth_send_file(filename):
    """
    Sends a file via bluetooth.

    This function tries to use "bluetooth-sendto", and if
    it is not available, it also tries "gnome-obex-send".
    """
    command_line = None

    if find_command('bluetooth-sendto'):
        command_line = ['bluetooth-sendto']
    elif find_command('gnome-obex-send'):
        command_line = ['gnome-obex-send']

    if command_line is not None:
        command_line.append(filename)
        return (Popen(command_line, close_fds=True).wait() == 0)
    else:
        logger.error('Cannot send file. Please install "bluetooth-sendto" or "gnome-obex-send".')
        return False


def format_time(seconds):
    """Format a seconds value to a string

    >>> format_time(0)
    '00:00'
    >>> format_time(20)
    '00:20'
    >>> format_time(3600)
    '01:00:00'
    >>> format_time(10921)
    '03:02:01'
    >>> format_time(86401)
    '24:00:01'
    """
    hours = 0
    minutes = 0
    if seconds >= 3600:
        hours = seconds // 3600
        seconds -= hours * 3600
    if seconds >= 60:
        minutes = seconds // 60
        seconds -= minutes * 60

    if hours == 0:
        return '%02d:%02d' % (minutes, seconds)
    else:
        return '%02d:%02d:%02d' % (hours, minutes, seconds)


def parse_time(value):
    """Parse a time string into seconds

    >>> parse_time('00:00')
    0
    >>> parse_time('00:00:00')
    0
    >>> parse_time('00:20')
    20
    >>> parse_time('00:00:20')
    20
    >>> parse_time('01:00:00')
    3600
    >>> parse_time('03:02:01')
    10921
    >>> parse_time('61:08')
    3668
    >>> parse_time('25:03:30')
    90210
    >>> parse_time('25:3:30')
    90210
    >>> parse_time('61.08')
    3668
    """
    if value == '':
        return 0

    if not value:
        raise ValueError('Invalid value: %s' % (str(value),))

    m = re.match(r'(\d+)[:.](\d\d?)[:.](\d\d?)', value)
    if m:
        hours, minutes, seconds = m.groups()
        return (int(hours) * 60 + int(minutes)) * 60 + int(seconds)

    m = re.match(r'(\d+)[:.](\d\d?)', value)
    if m:
        minutes, seconds = m.groups()
        return int(minutes) * 60 + int(seconds)

    return int(value)


def format_seconds_to_hour_min_sec(seconds):
    """
    Take the number of seconds and format it into a
    human-readable string (duration).

    >>> format_seconds_to_hour_min_sec(3834)
    '1 hour, 3 minutes and 54 seconds'
    >>> format_seconds_to_hour_min_sec(3600)
    '1 hour'
    >>> format_seconds_to_hour_min_sec(62)
    '1 minute and 2 seconds'
    """

    if seconds < 1:
        return N_('%(count)d second', '%(count)d seconds',
                  seconds) % {'count': seconds}

    result = []

    seconds = int(seconds)

    hours = seconds // 3600
    seconds = seconds % 3600

    minutes = seconds // 60
    seconds = seconds % 60

    if hours:
        result.append(N_('%(count)d hour', '%(count)d hours',
                         hours) % {'count': hours})

    if minutes:
        result.append(N_('%(count)d minute', '%(count)d minutes',
                         minutes) % {'count': minutes})

    if seconds:
        result.append(N_('%(count)d second', '%(count)d seconds',
                         seconds) % {'count': seconds})

    if len(result) > 1:
        return (' ' + _('and') + ' ').join((', '.join(result[:-1]), result[-1]))
    else:
        return result[0]


def http_request(url, method='HEAD'):
    (scheme, netloc, path, params, query, fragment) = urllib.parse.urlparse(url)
    if scheme == 'https':
        conn = http.client.HTTPSConnection(netloc)
    else:
        conn = http.client.HTTPConnection(netloc)
    start = len(scheme) + len('://') + len(netloc)
    conn.request(method, url[start:])
    return conn.getresponse()


def gui_open(filename, gui=None):
    """
    Open a file or folder with the default application set
    by the Desktop environment. This uses "xdg-open" on all
    systems with a few exceptions:

       on Win32, os.startfile() is used
    """
    try:
        if gpodder.ui.win32:
            os.startfile(filename)
            opener = None
        elif gpodder.ui.osx:
            opener = 'open'
        else:
            opener = 'xdg-open'

        if opener:
            opener_fullpath = shutil.which(opener)
            if opener_fullpath is None:
                raise Exception((_("System default program '%(opener)s' not found"))
                    % {'opener': opener}
                )
            Popen([opener_fullpath, filename], close_fds=True)
        return True
    except:
        logger.error('Cannot open file/folder: "%s"', filename, exc_info=True)
        if gui is not None:
            if opener is None:
                message = _("Cannot open file/folder '%(filename)s' using default program") % {'filename': filename}
            else:
                message = _("Cannot open '%(filename)s' using '%(opener)s'") \
                                        % {'filename': filename, 'opener': opener}
            gui.show_message_details(_('Cannot open file/folder'),
                    str(sys.exc_info()[1]), message)
        return False


def open_website(url):
    """
    Opens the specified URL using the default system web
    browser. This uses Python's "webbrowser" module, so
    make sure your system is set up correctly.
    """
    run_in_background(lambda: webbrowser.open(url))
    return True


def copy_text_to_clipboard(text):
    """
    Copies the specified text to both clipboards.
    """
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gdk, Gtk

    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
    clipboard.set_text(text, -1)
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)


def convert_bytes(d):
    """
    Convert byte strings to unicode strings

    This function will decode byte strings into unicode
    strings. Any other data types will be left alone.

    >>> convert_bytes(None)
    >>> convert_bytes(4711)
    4711
    >>> convert_bytes(True)
    True
    >>> convert_bytes(3.1415)
    3.1415
    >>> convert_bytes('Hello')
    'Hello'
    >>> type(convert_bytes(b'hoho'))
    <class 'bytes'>
    """
    if d is None:
        return d
    elif isinstance(d, bytes):
        return d
    elif any(isinstance(d, t) for t in (int, int, bool, float)):
        return d
    elif not isinstance(d, str):
        return d.decode('utf-8', 'ignore')
    return d


def sanitize_filename(filename, max_length):
    """
    Generate a sanitized version of a filename; trim filename
    if greater than max_length (0 = no limit).

    >>> sanitize_filename('https://www.host.name/feed', 0)
    'https___www.host.name_feed'
    >>> sanitize_filename('Binärgewitter', 0)
    'Binärgewitter'
    >>> sanitize_filename('Cool feed (ogg)', 0)
    'Cool feed (ogg)'
    >>> sanitize_filename('Cool feed (ogg)', 1)
    'C'
    """
    if max_length > 0 and len(filename) > max_length:
        logger.info('Limiting file/folder name "%s" to %d characters.', filename, max_length)
        filename = filename[:max_length]

    # see #361 - at least slash must be removed
    filename = re.sub(r"[\"*/:<>?\\|]", "_", filename)

    return filename.strip('.' + string.whitespace)


def sanitize_filename_ext(filename, ext, max_length, max_length_with_ext):
    """
    Generate a sanitized version of a filename and extension.
    Truncate filename if greater than max_length.
    Truncate extension if filename.extension is greater than max_length_with_ext.
    :param str filename: filename without extension
    :param str ext: extension
    :return (str, str): (sanitized_truncated_filename, sanitized_extension)

    >>> sanitize_filename_ext('podcast_4987_faz_essay_der_podcast_fur_die_geschichte' \
                              '_hinter_den_nachrichten_episode_4_04_die_macht_der_tater_brechen', \
                              ".mp3", 120, 131)
    ('podcast_4987_faz_essay_der_podcast_fur_die_geschichte_hinter_den_nachrichten_episode_4_04_die_macht_der_tater_brechen', '.mp3')
    """
    sanitized_fn = sanitize_filename(filename, max_length)
    sanitized_ext = sanitize_filename(ext, max_length_with_ext - len(sanitized_fn))
    return (sanitized_fn, ('.' + sanitized_ext) if sanitized_ext else '')


def find_mount_point(directory):
    """
    Try to find the mount point for a given directory.
    If the directory is itself a mount point, return
    it. If not, remove the last part of the path and
    re-check if it's a mount point. If the directory
    resides on your root filesystem, "/" is returned.

    >>> find_mount_point('/')
    '/'

    >>> find_mount_point(b'/something')
    Traceback (most recent call last):
      ...
    ValueError: Convert bytes objects to str first.

    >>> find_mount_point(None)
    Traceback (most recent call last):
      ...
    ValueError: Directory names should be of type str.

    >>> find_mount_point(42)
    Traceback (most recent call last):
      ...
    ValueError: Directory names should be of type str.

    >>> from minimock import mock, restore
    >>> mocked_mntpoints = ('/', '/home', '/media/usbdisk', '/media/cdrom')
    >>> mock('os.path.ismount', returns_func=lambda x: x in mocked_mntpoints)
    >>>
    >>> # For mocking os.getcwd(), we simply use a lambda to avoid the
    >>> # massive output of "Called os.getcwd()" lines in this doctest
    >>> os.getcwd = lambda: '/home/thp'
    >>>
    >>> find_mount_point('.')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('relativity')
    Called os.path.ismount('/home/thp/relativity')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/usbdisk/')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> find_mount_point('/home/thp/Desktop')
    Called os.path.ismount('/home/thp/Desktop')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/usbdisk/Podcasts/With Spaces')
    Called os.path.ismount('/media/usbdisk/Podcasts/With Spaces')
    Called os.path.ismount('/media/usbdisk/Podcasts')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> find_mount_point('/home/')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/cdrom/../usbdisk/blubb//')
    Called os.path.ismount('/media/usbdisk/blubb')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> restore()
    """
    if isinstance(directory, bytes):
        # We do not accept byte strings, because they could fail when
        # trying to be converted to some native encoding, so fail loudly
        # and leave it up to the callee to decode from the proper encoding.
        raise ValueError('Convert bytes objects to str first.')

    if not isinstance(directory, str):
        # In Python 2, we assumed it's a byte str; in Python 3, we assume
        # that it's a unicode str. The abspath/ismount/split functions of
        # os.path work with unicode str in Python 3, but not in Python 2.
        raise ValueError('Directory names should be of type str.')

    directory = os.path.abspath(directory)

    while directory != '/':
        if os.path.ismount(directory):
            return directory
        else:
            (directory, tail_data) = os.path.split(directory)

    return '/'


# matches http:// and ftp:// and mailto://
protocolPattern = re.compile(r'^\w+://')


def isabs(string):
    """
    @return true if string is an absolute path or protocoladdress
    for addresses beginning in http:// or ftp:// or ldap:// -
    they are considered "absolute" paths.
    Source: http://code.activestate.com/recipes/208993/
    """
    if protocolPattern.match(string): return 1
    return os.path.isabs(string)


def relpath(p1, p2):
    """
    Finds relative path from p2 to p1, like os.path.relpath but handles
    uris. Returns None if no such path exists due to the paths being on
    different devices.
    """
    u1 = urllib.parse.urlparse(p1)
    u2 = urllib.parse.urlparse(p2)
    if u1.scheme and u2.scheme and (u1.scheme != u2.scheme or u1.netloc != u2.netloc):
        return None
    return os.path.relpath(u1.path, u2.path)


def get_hostname():
    """Return the hostname of this computer

    This can be implemented in a different way on each
    platform and should yield a unique-per-user device ID.
    """
    nodename = platform.node()

    if nodename:
        return nodename

    # Fallback - but can this give us "localhost"?
    return socket.gethostname()


def detect_device_type():
    """Device type detection for gpodder.net

    This function tries to detect on which
    kind of device gPodder is running on.

    Possible return values:
    desktop, laptop, mobile, server, other
    """
    if glob.glob('/proc/acpi/battery/*'):
        # Linux: If we have a battery, assume Laptop
        return 'laptop'

    return 'desktop'


def write_m3u_playlist(m3u_filename, episodes, extm3u=True):
    """Create an M3U playlist from a episode list

    If the parameter "extm3u" is False, the list of
    episodes should be a list of filenames, and no
    extended information will be written into the
    M3U files (#EXTM3U / #EXTINF).

    If the parameter "extm3u" is True (default), then the
    list of episodes should be PodcastEpisode objects,
    as the extended metadata will be taken from them.
    """
    f = open(m3u_filename, 'w')

    if extm3u:
        # Mandatory header for extended playlists
        f.write('#EXTM3U\n')

    for episode in episodes:
        if not extm3u:
            # Episode objects are strings that contain file names
            f.write(episode + '\n')
            continue

        if episode.was_downloaded(and_exists=True):
            filename = episode.local_filename(create=False)
            assert filename is not None

            if os.path.dirname(filename).startswith(os.path.dirname(m3u_filename)):
                filename = filename[len(os.path.dirname(m3u_filename) + os.sep):]
            f.write('#EXTINF:0,' + episode.playlist_title() + '\n')
            f.write(filename + '\n')

    f.close()


def generate_names(filename):
    basename, ext = os.path.splitext(filename)
    for i in itertools.count():
        if i:
            yield '%s (%d)%s' % (basename, i + 1, ext)
        else:
            yield filename


def is_known_redirecter(url):
    """Check if a URL redirect is expected, and no filenames should be updated

    We usually honor URL redirects, and update filenames accordingly.
    In some cases (e.g. Soundcloud) this results in a worse filename,
    so we hardcode and detect these cases here to avoid renaming files
    for which we know that a "known good default" exists.

    The problem here is that by comparing the currently-assigned filename
    with the new filename determined by the URL, we cannot really determine
    which one is the "better" URL (e.g. "n5rMSpXrqmR9.128.mp3" for Soundcloud).
    """

    # Soundcloud-hosted media downloads (we take the track name as filename)
    if url.startswith('http://ak-media.soundcloud.com/'):
        return True

    return False


def atomic_rename(old_name, new_name):
    """Atomically rename/move a (temporary) file

    This is usually used when updating a file safely by writing
    the new contents into a temporary file and then moving the
    temporary file over the original file to replace it.
    """
    if gpodder.ui.win32:
        # Win32 does not support atomic rename with os.rename
        shutil.move(old_name, new_name)
    else:
        os.rename(old_name, new_name)


def check_command(self, cmd):
    """Check if a command line command/program exists"""
    # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
    program = shlex.split(cmd)[0]
    return (find_command(program) is not None)


def rename_episode_file(episode, filename):
    """Helper method to update a PodcastEpisode object

    Useful after renaming/converting its download file.
    """
    if not os.path.exists(filename):
        raise ValueError('Target filename does not exist.')

    basename, extension = os.path.splitext(filename)

    episode.download_filename = os.path.basename(filename)
    episode.file_size = os.path.getsize(filename)
    episode.mime_type = mimetype_from_extension(extension)
    episode.save()
    episode.db.commit()


def get_update_info():
    """
    Get up to date release information from gpodder.org.

    Returns a tuple: (up_to_date, latest_version, release_date, days_since)

    Example result (up to date version, 20 days after release):
        (True, '3.0.4', '2012-01-24', 20)

    Example result (outdated version, 10 days after release):
        (False, '3.0.5', '2012-02-29', 10)
    """
    url = 'https://api.github.com/repos/gpodder/gpodder/releases/latest'
    info = urlopen(url).json()

    latest_version = info.get('tag_name', '').replace('gpodder-', '')
    release_date = info['published_at']

    release_parsed = datetime.datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%SZ')
    days_since_release = (datetime.datetime.today() - release_parsed).days

    def convert(s):
        # Use both public and local version label, see PEP 440
        pubv, locv = next(
            (v[0], v[1] if len(v) > 1 else '') for v in (s.split('+'),))
        return tuple(int(x) if x.isdigit() else x.lower()
            for x in pubv.split('.') + (locv.split('.') if locv else []))

    up_to_date = (convert(gpodder.__version__) >= convert(latest_version))

    return up_to_date, latest_version, release_date, days_since_release


def run_in_background(function, daemon=False):
    logger.debug('run_in_background: %s (%s)', function, str(daemon))
    thread = threading.Thread(target=function)
    thread.setDaemon(daemon)
    thread.start()
    return thread


def linux_get_active_interfaces():
    """Get active network interfaces using 'ip addr'

    A generator function yielding network interface
    names with an inet (or inet6) and a broadcast
    address, indicating an active network connection
    """
    process = Popen(
        ['ip', 'addr', 'show', 'scope', 'global', 'up'],
        close_fds=True, stdout=subprocess.PIPE)
    data, x = process.communicate()
    for record in re.split(r'^\d+: ',
                           data.decode(locale.getpreferredencoding()),
                           flags=re.MULTILINE):
        mo = re.match(r'^([^:]*):.*inet.*scope', record, flags=re.DOTALL)
        if mo:
            yield mo.group(1)


def osx_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = Popen(['ifconfig'], close_fds=True, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split(r'\n(?!\t)', stdout.decode('utf-8'), re.MULTILINE):
        b = re.match(r'(\w+):.*status: (active|associated)$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)


def unix_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = Popen(['ifconfig'], close_fds=True, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split(r'\n(?!\t)', stdout.decode(locale.getpreferredencoding()), re.MULTILINE):
        b = re.match(r'(\w+):.*status: (active|associated)$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)


def connection_available():
    """Check if an Internet connection is available

    Returns True if a connection is available (or if there
    is no way to determine the connection). Returns False
    if no network interfaces are up (i.e. no connectivity).
    """
    try:
        if gpodder.ui.win32:
            # FIXME: Implement for Windows
            return True
        elif gpodder.ui.osx:
            return len(list(osx_get_active_interfaces())) > 0
        else:
            # By default, we assume we're online (bug 1730)
            online = True

            if find_command('ip') is not None:
                online = bool(list(linux_get_active_interfaces()))
            elif find_command('ifconfig') is not None:
                # If ifconfig is available, and it says we don't have
                # any active interfaces, assume we're offline
                online = bool(list(unix_get_active_interfaces()))

            return online

    except Exception as e:
        logger.warning('Cannot get connection status: %s', e, exc_info=True)
        # When we can't determine the connection status, act as if we're online (bug 1730)
        return True


def website_reachable(url):
    """
    Check if a specific website is available.
    """
    if not connection_available():
        # No network interfaces up - assume website not reachable
        return (False, None)

    try:
        response = requests.get(url, timeout=1)
        return (True, response)
    except requests.exceptions.RequestException:
        pass

    return (False, None)


def delete_empty_folders(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in dirs:
            dirname = os.path.join(root, name)
            if not os.listdir(dirname):
                os.rmdir(dirname)


def guess_encoding(filename):
    """
    read filename encoding as defined in PEP 263
    - BOM marker => utf-8
    - coding: xxx comment in first 2 lines
    - else return None
    >>> guess_encoding("not.there")
    >>> guess_encoding("setup.py")
    >>> guess_encoding("share/gpodder/extensions/mpris-listener.py")
    'utf-8'
    """
    def re_encoding(line):
        m = re.match(b"""^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)""", line)
        if m:
            return m.group(1).decode()
        else:
            return None

    if not filename or not os.path.exists(filename):
        return None

    with open(filename, "rb") as f:
        fst = f.readline()
        if fst[:3] == b"\xef\xbb\xbf":
            return "utf-8"
        encoding = re_encoding(fst)
        if not encoding:
            snd = f.readline()
            encoding = re_encoding(snd)
    return encoding


def iri_to_url(url):
    """
    Properly escapes Unicode characters in the URL path section
    TODO: Explore if this should also handle the domain
    Based on: http://stackoverflow.com/a/18269491/1072626
    In response to issue: https://github.com/gpodder/gpodder/issues/232

    >>> iri_to_url('http://www.valpskott.se/Valpcast/MP3/Valpcast%20-%20Existentiella%20frÃ¥gor.mp3')
    'http://www.valpskott.se/Valpcast/MP3/Valpcast%20-%20Existentiella%20fr%C3%83%C2%A5gor.mp3'

    See https://github.com/gpodder/gpodder/issues/399
    >>> iri_to_url('//dts.podtrac.com/redirect.mp3/http://myhost/myepisode.mp3')
    '//dts.podtrac.com/redirect.mp3/http://myhost/myepisode.mp3'
    """
    url = urllib.parse.urlsplit(url)
    url = list(url)
    # First unquote to avoid escaping quoted content
    url[2] = urllib.parse.unquote(url[2])
    # extend safe with all allowed chars in path segment of URL, cf pchar rule
    # in https://tools.ietf.org/html/rfc3986#appendix-A
    url[2] = urllib.parse.quote(url[2], safe="/-._~!$&'()*+,;=:@")
    url = urllib.parse.urlunsplit(url)
    return url


class Popen(subprocess.Popen):

    """A Popen process that tries not to leak file descriptors.

    This is a drop-in replacement for subprocess.Popen(), which takes the same
    arguments.

    'close_fds' will default to True, if omitted. This stops the process from
    inheriting ALL of gPodder's file descriptors, which would keep them
    'in-use'. That is of particular concern whenever the download queue is
    active and interacting with the filesystem in the background.

    On Windows however, redirection cannot coexist with 'close_fds=True'.
    Specifying both will raise a ValueError. A message will appear in the log.

    For communication with short-lived Windows commands, setting 'close_fds'
    to False may be a tolerable risk. Otherwise as a last resort, sending
    output to temp files to read afterward might work (probably involving
    'shell=True').

    See https://github.com/gpodder/gpodder/issues/420
    """

    def __init__(self, *args, **kwargs):
        self.__logged_returncode = False

        if 'close_fds' not in kwargs:
            kwargs['close_fds'] = True

        try:
            super(Popen, self).__init__(*args, **kwargs)  # Python 2 syntax

        except (ValueError) as e:
            if gpodder.ui.win32 and kwargs['close_fds']:
                if [(k, v) for (k, v) in kwargs.items() if k in ('stdin', 'stdout', 'stderr') and v]:
                    logger = logging.getLogger(__name__)
                    logger.error('util.Popen(close_fds=True) is incompatible with'
                                 ' stream redirection on Windows.')
                    logger.error('With close_fds=False, the process keeps all '
                                 'currently open files locked. It might be tolerable '
                                 'for short-lived commands. Or use temp files.')

            raise e

    @classmethod
    def testPopen():
        # Problematic commands (write to stderr or read from stdin).
        if gpodder.ui.win32:
            cmd = ['findstr.exe', '/!']
            cmd_pipe = ['findstr', 'hello']
        else:
            cmd = ['cat', '--helpp']
            cmd_pipe = ['grep', 'hello']

        logger.info('Test #1: Implicit close_fds=True, with no redirection')
        logger.info('No race condition.')
        logger.info('Streams left in the console.')
        logger.info('Typical spawn and forget. Might as well wait().')
        p = Popen(cmd)
        out, err = p.communicate()
        print("- - stderr - -\n{}\n- - -    - - -\n".format(err))

        logger.info('Test #2: Explicit close_fds=False, with redirection.')
        logger.info('This has a race condition, but communicate() always returns streams.')
        p = Popen(cmd, close_fds=False, stderr=subprocess.PIPE, universal_newlines=True)
        out, err = p.communicate()
        print("- - stderr - -\n{}\n- - -    - - -\n".format(err))

        try:
            logger.info('Test #3: Implicit close_fds=True, with attempted redirection.')
            logger.info('No race condition.')
            logger.info('On Windows, this will raise ValueError.')
            logger.info('Other platforms will have readable streams returned.')
            p = Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
            out, err = p.communicate()
            print("- - stderr - -\n{}\n- - -    - - -\n".format(err))

        except (ValueError) as e:
            print("- - Caught - -\n{}: {}\n- - -    - - -\n".format(e.__class__.__name__, e))

        try:
            logger.info('Test #4: Implicit close_fds=True, given input.')
            p = Popen(cmd_pipe, stdin=subprocess.PIPE)
            out, err = p.communicate(input=b'hello world')
            print("NEVER REACHED ON WINDOWS")
            print("- - stderr - -\n{}\n- - -    - - -\n".format(err))

        except (ValueError) as e:
            print("- - Caught - -\n{}: {}\n- - -    - - -\n".format(e.__class__.__name__, e))

        logger.info('Log spam only occurs if returncode is non-zero or if explaining the Windows redirection error.')


def _parse_mimetype_sorted_dictitems(mimetype):
    """ python 3.5 unordered dict compat for doctest. don't use! """
    r = parse_mimetype(mimetype)
    return r[0], r[1], sorted(r[2].items())


def parse_mimetype(mimetype):
    """
    parse mimetype into (type, subtype, parameters)
    see RFC 2045 §5.1
    TODO: unhandled comments and continuations

    >>> _parse_mimetype_sorted_dictitems('application/atom+xml;profile=opds-catalog;type=feed;kind=acquisition')
    ('application', 'atom+xml', [('kind', 'acquisition'), ('profile', 'opds-catalog'), ('type', 'feed')])
    >>> _parse_mimetype_sorted_dictitems('application/atom+xml; profile=opds-catalog ; type=feed ; kind=acquisition')
    ('application', 'atom+xml', [('kind', 'acquisition'), ('profile', 'opds-catalog'), ('type', 'feed')])
    >>> _parse_mimetype_sorted_dictitems(None)
    (None, None, [])
    >>> _parse_mimetype_sorted_dictitems('')
    (None, None, [])
    >>> _parse_mimetype_sorted_dictitems('application/x-myapp;quoted="a quoted string with ; etc.";a=b')
    ('application', 'x-myapp', [('a', 'b'), ('quoted', 'a quoted string with ; etc.')])
    """
    class MIMETypeException(Exception):
        """ when an exception is encountered parsing mime type """

    if not mimetype or '/' not in mimetype:
        return (None, None, {})
    main, sub = mimetype.split('/', 1)
    try:
        sub, rawparams = sub.split(';', 1)
        params = {}
        key = ''
        value = ''
        invalue = False
        inquotes = False
        quotedvalue = False
        nomore = False
        offset = len(main) + 1 + len(sub) + 1
        for i, c in enumerate(rawparams):
            if inquotes:
                if c == '"':
                    inquotes = False
                    quotedvalue = True
                    nomore = True
                else:
                    value += c
                continue
            if c == ';':
                if invalue:
                    params[key] = value
                    key = ''
                    invalue = False
                    inquotes = False
                    nomore = False
                else:
                    raise MIMETypeException("Unable to parse mimetype '%s': unexpected ; at %i" % (mimetype, offset + i))
            elif c == '"':
                if invalue:
                    if value:
                        raise MIMETypeException("Unable to parse mimetype '%s': unexpected \" at %i" % (mimetype, offset + i))
                    inquotes = True
            elif c == '=':
                if invalue:
                    raise MIMETypeException("Unable to parse mimetype '%s': unexpected = at %i" % (mimetype, offset + i))
                invalue = True
                quotedvalue = False
                value = ''
            elif c in (' ', '\t'):
                if invalue and value:
                    nomore = True
                if not invalue and key:
                    nomore = True
            else:
                if nomore:
                    raise MIMETypeException("Unable to parse mimetype '%s': unexpected %s after space at %i" % (mimetype, c, offset + i))
                if invalue:
                    value += c
                else:
                    key += c
        # after loop
        if invalue:
            if value or quotedvalue:
                params[key] = value
            else:
                raise MIMETypeException("Unable to parse mimetype '%s': empty value for %s" % (mimetype, key))
        elif key:
            raise MIMETypeException("Unable to parse mimetype '%s': missing value for %s" % (mimetype, key))
        elif inquotes:
            raise MIMETypeException("Unable to parse mimetype '%s': unclosed \"" % mimetype)
        return (main, sub, params)
    except MIMETypeException as e:
        print(e)
        return (None, None, {})


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
        headers_string = ['%s:%s' % (k, v) for k, v in list(headers.items())]
        msg = email.message_from_string('\n'.join(headers_string))
        if header_name in msg:
            raw_value = msg.get_param(param, header=header_name)
            if raw_value is not None:
                value = email.utils.collapse_rfc2231_value(raw_value)
    except Exception as e:
        logger.error('Cannot get %s from %s', param, header_name, exc_info=True)

    return value


def response_text(response, default_encoding='utf-8'):
    """
    Utility method to return urlopen response's text.
    Requests uses only the charset info in content-type, then defaults to ISO-8859-1
    when content-type=text/*.
    We could use chardet (via response.apparent_encoding) but it's slow so often it's
    simpler to just use the known encoding.
    :return: textual body of the response
    """
    if 'charset=' in response.headers.get('content-type'):
        return response.text
    else:
        return response.content.decode(default_encoding)


def mount_volume_for_file(file, op=None):
    """
    Utility method to mount the enclosing volume for the given file in a blocking
    fashion
    """
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib
    if gpodder.ui.gtk:
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    else:
        loop = GLib.MainLoop()

    result = True
    message = None

    def callback(file, res):
        nonlocal result, message
        try:
            file.mount_enclosing_volume_finish(res)
            result = True
        except GLib.Error as err:
            if (not err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_SUPPORTED)
                    and not err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.ALREADY_MOUNTED)):
                message = err.message
                result = False
        finally:
            if gpodder.ui.gtk:
                Gtk.main_quit()
            else:
                loop.quit()

    file.mount_enclosing_volume(Gio.MountMountFlags.NONE, op, None, callback)
    if gpodder.ui.gtk:
        Gtk.main()
    else:
        loop.run()
    return result, message


def scale_pixbuf(pixbuf, max):
    from gi.repository import GdkPixbuf

    w_cur = pixbuf.get_width()
    h_cur = pixbuf.get_height()

    if w_cur <= max and h_cur <= max:
        return pixbuf

    f = max / (w_cur if w_cur >= h_cur else h_cur)
    w_new = int(w_cur * f)
    h_new = int(h_cur * f)

    return pixbuf.scale_simple(w_new, h_new, GdkPixbuf.InterpType.BILINEAR)
