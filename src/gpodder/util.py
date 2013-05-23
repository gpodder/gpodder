# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

import gpodder

import logging
logger = logging.getLogger(__name__)

import os
import os.path
import platform
import glob
import stat
import shlex
import shutil
import socket
import sys
import string

import re
import subprocess
from html.entities import entitydefs
import time
import gzip
import datetime
import threading
import tempfile

import urllib.error
import urllib.parse
import urllib.request
import http.client
import webbrowser
import mimetypes
import itertools
import contextlib

from email.utils import mktime_tz, parsedate_tz


import io
import xml.dom.minidom

_ = gpodder.gettext
N_ = gpodder.ngettext

import locale
try:
    locale.setlocale(locale.LC_ALL, '')
except Exception as e:
    logger.warn('Cannot set locale (%s)', e, exc_info=True)

# Native filesystem encoding detection
encoding = sys.getfilesystemencoding()

if encoding is None:
    if 'LANG' in os.environ and '.' in os.environ['LANG']:
        lang = os.environ['LANG']
        (language, encoding) = lang.rsplit('.', 1)
        logger.info('Detected encoding: %s', encoding)
    else:
        encoding = 'utf-8'


# Filename / folder name sanitization
def _sanitize_char(c):
    if c in string.whitespace:
        return ' '
    elif c in ',-.()':
        return c
    elif c in string.punctuation or ord(c) <= 31:
        return '_'

    return c

SANITIZATION_TABLE = ''.join(map(_sanitize_char, list(map(chr, list(range(256))))))
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
]

_MIME_TYPES = dict((k, v) for v, k in _MIME_TYPE_LIST)
_MIME_TYPES_EXT = dict(_MIME_TYPE_LIST)


def make_directory( path):
    """
    Tries to create a directory if it does not exist already.
    Returns True if the directory exists after the function 
    call, False otherwise.
    """
    if os.path.isdir( path):
        return True

    try:
        os.makedirs( path)
    except:
        logger.warn('Could not create directory: %s', path)
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
    """
    if not url or len(url) < 8:
        return None

    # This is a list of prefixes that you can use to minimize the amount of
    # keystrokes that you have to use.
    # Feel free to suggest other useful prefixes, and I'll add them here.
    PREFIXES = {
            'fb:': 'http://feeds.feedburner.com/%s',
            'yt:': 'http://www.youtube.com/rss/user/%s/videos.rss',
            'sc:': 'http://soundcloud.com/%s',
            'fm4od:': 'http://onapp1.orf.at/webcam/fm4/fod/%s.xspf',
            # YouTube playlists. To get a list of playlists per-user, use:
            # https://gdata.youtube.com/feeds/api/users/<username>/playlists
            'ytpl:': 'http://gdata.youtube.com/feeds/api/playlists/%s',
    }

    for prefix, expansion in PREFIXES.items():
        if url.startswith(prefix):
            url = expansion % (url[len(prefix):],)
            break

    # Assume HTTP for URLs without scheme
    if not '://' in url:
        url = 'http://' + url

    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)

    # Schemes and domain names are case insensitive
    scheme, netloc = scheme.lower(), netloc.lower()

    # Normalize empty paths to "/"
    if path == '':
        path = '/'

    # feed://, itpc:// and itms:// are really http://
    if scheme in ('feed', 'itpc', 'itms'):
        scheme = 'http'

    if scheme not in ('http', 'https', 'ftp', 'file'):
        return None

    # urlunsplit might return "a slighty different, but equivalent URL"
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
    ValueError: URL has to be a string or unicode object.
    >>> username_password_from_url(None)
    Traceback (most recent call last):
      ...
    ValueError: URL has to be a string or unicode object.
    >>> username_password_from_url('http://a@b:c@host.com/')
    ('a@b', 'c')
    >>> username_password_from_url('ftp://a:b:c@host.com/')
    ('a', 'b:c')
    >>> username_password_from_url('http://i%2Fo:P%40ss%3A@host.com/')
    ('i/o', 'P@ss:')
    >>> username_password_from_url('ftp://%C3%B6sterreich@host.com/')
    ('\xf6sterreich', None)
    >>> username_password_from_url('http://w%20x:y%20z@example.org/')
    ('w x', 'y z')
    >>> username_password_from_url('http://example.com/x@y:z@test.com/')
    (None, None)
    """
    if type(url) not in (str, str):
        raise ValueError('URL has to be a string or unicode object.')

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

def calculate_size( path):
    """
    Tries to calculate the size of a directory, including any 
    subdirectories found. The returned value might not be 
    correct if the user doesn't have appropriate permissions 
    to list all subdirectories of the given path.
    """
    if path is None:
        return 0

    if os.path.dirname( path) == '/':
        return 0

    if os.path.isfile( path):
        return os.path.getsize( path)

    if os.path.isdir( path) and not os.path.islink( path):
        sum = os.path.getsize( path)

        try:
            for item in os.listdir(path):
                try:
                    sum += calculate_size(os.path.join(path, item))
                except:
                    logger.warn('Cannot get size for %s', path, exc_info=True)
        except:
            logger.warn('Cannot access %s', path, exc_info=True)

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
        logger.warn('Cannot get mtime for %s', filename, exc_info=True)
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
        return (datetime.datetime.now()-dt).days


def file_age_to_string(days): # XXX Unused
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
        return N_('%(count)d day ago', '%(count)d days ago', days) % {'count':days}


def get_free_disk_space(path): # XXX Unused
    """
    Calculates the free disk space available to the current user
    on the file system that contains the given path.

    If the path (or its parent folder) does not yet exist, this
    function returns zero.
    """

    if not os.path.exists(path):
        return 0

    s = os.statvfs(path)

    return s.f_bavail * s.f_bsize


def format_date(timestamp): # XXX Unused
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

    seconds_in_a_day = 60*60*24

    today = time.localtime()[:3]
    yesterday = time.localtime(time.time() - seconds_in_a_day)[:3]
    try:
        timestamp_date = time.localtime(timestamp)[:3]
    except ValueError as ve:
        logger.warn('Cannot convert timestamp', exc_info=True)
        return None
    
    if timestamp_date == today:
       return _('Today')
    elif timestamp_date == yesterday:
       return _('Yesterday')
   
    try:
        diff = int( (time.time() - timestamp)/seconds_in_a_day )
    except:
        logger.warn('Cannot convert "%s" to date.', timestamp, exc_info=True)
        return None

    try:
        timestamp = datetime.datetime.fromtimestamp(timestamp)
    except:
        return None

    if diff < 7:
        # Weekday name
        return str(timestamp.strftime('%A').decode(encoding))
    else:
        # Locale's appropriate date representation
        return str(timestamp.strftime('%x'))


def format_filesize(bytesize, use_si_units=False, digits=2): # XXX Unused
    """
    Formats the given size in bytes to be human-readable, 

    Returns a localized "(unknown)" string when the bytesize
    has a negative value.
    """
    si_units = (
            ( 'kB', 10**3 ),
            ( 'MB', 10**6 ),
            ( 'GB', 10**9 ),
    )

    binary_units = (
            ( 'KiB', 2**10 ),
            ( 'MiB', 2**20 ),
            ( 'GiB', 2**30 ),
    )

    try:
        bytesize = float( bytesize)
    except:
        return _('(unknown)')

    if bytesize < 0:
        return _('(unknown)')

    if use_si_units:
        units = si_units
    else:
        units = binary_units

    ( used_unit, used_value ) = ( 'B', bytesize )

    for ( unit, value ) in units:
        if bytesize >= value:
            used_value = bytesize / float(value)
            used_unit = unit

    return ('%.'+str(digits)+'f %s') % (used_value, used_unit)


def delete_file(filename):
    """Delete a file from the filesystem

    Errors (permissions errors or file not found)
    are silently ignored.
    """
    try:
        os.remove(filename)
    except Exception as e:
        logger.warn('Cannot delete file: %s', filename, exc_info=True)


def remove_html_tags(html):
    """
    Remove HTML tags from a string and replace numeric and
    named entities with the corresponding character, so the 
    HTML text can be displayed in a simple text view.
    """
    if html is None:
        return None

    # If we would want more speed, we could make these global
    re_strip_tags = re.compile('<[^>]*>')
    re_unicode_entities = re.compile('&#(\d{2,4});')
    re_html_entities = re.compile('&(.{2,8});')
    re_newline_tags = re.compile('(<br[^>]*>|<[/]?ul[^>]*>|</li>)', re.I)
    re_listing_tags = re.compile('<li[^>]*>', re.I)

    result = html
    
    # Convert common HTML elements to their text equivalent
    result = re_newline_tags.sub('\n', result)
    result = re_listing_tags.sub('\n * ', result)
    result = re.sub('<[Pp]>', '\n\n', result)

    # Remove all HTML/XML tags from the string
    result = re_strip_tags.sub('', result)

    # Convert numeric XML entities to their unicode character
    result = re_unicode_entities.sub(lambda x: chr(int(x.group(1))), result)

    # Convert named HTML entities to their unicode character
    result = re_html_entities.sub(lambda x: entitydefs.get(x.group(1),''), result)
    
    # Convert more than two newlines to two newlines
    result = re.sub('([\r\n]{2})([\r\n])+', '\\1', result)

    return result.strip()


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


def mimetype_from_extension(extension): # XXX Only used in WebUI
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
    type, encoding = mimetypes.guess_type('file'+extension)

    return type or ''


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
    (scheme, netloc, path, para, query, fragid) = urllib.parse.urlparse(url)
    (filename, extension) = os.path.splitext(os.path.basename( urllib.parse.unquote(path)))

    if file_type_by_extension(extension) is not None and not \
        query.startswith(scheme+'://'):
        # We have found a valid extension (audio, video)
        # and the query string doesn't look like a URL
        return ( filename, extension.lower() )

    # If the query string looks like a possible URL, try that first
    if len(query.strip()) > 0 and query.find('/') != -1:
        query_url = '://'.join((scheme, urllib.parse.unquote(query)))
        (query_filename, query_extension) = filename_from_url(query_url)

        if file_type_by_extension(query_extension) is not None:
            return os.path.splitext(os.path.basename(query_url))

    # No exact match found, simply return the original filename & extension
    return ( filename, extension.lower() )


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
    type, encoding = mimetypes.guess_type('file'+extension)

    if type is not None and '/' in type:
        filetype, rest = type.split('/', 1)
        if filetype in ('audio', 'video', 'image'):
            return filetype
    
    return None


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


def urlopen(url, headers=None, data=None, timeout=None):
    """
    An URL opener with the User-agent set to gPodder (with version)
    """
    username, password = username_password_from_url(url)
    if username is not None or password is not None:
        url = url_strip_authentication(url)
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, username, password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()

    if headers is None:
        headers = {}
    else:
        headers = dict(headers)

    headers.update({'User-agent': gpodder.user_agent})
    request = urllib.request.Request(url, data=data, headers=headers)
    if timeout is None:
        return opener.open(request)
    else:
        return opener.open(request, timeout=timeout)


def find_command(command):
    """
    Searches the system's PATH for a specific command that is
    executable by the user. Returns the first occurence of an
    executable binary in the PATH, or None if the command is
    not available.
    """

    if 'PATH' not in os.environ:
        return None

    for path in os.environ['PATH'].split(os.pathsep):
        command_file = os.path.join(path, command)
        if os.path.isfile(command_file) and os.access(command_file, os.X_OK):
            return command_file

    return None


def format_time(value): # XXX Unused
    """Format a seconds value to a string

    >>> format_time(0)
    '00:00'
    >>> format_time(20)
    '00:20'
    >>> format_time(3600)
    '01:00:00'
    >>> format_time(10921)
    '03:02:01'
    """
    dt = datetime.datetime.utcfromtimestamp(value)
    if dt.hour == 0:
        return dt.strftime('%M:%S')
    else:
        return dt.strftime('%H:%M:%S')


def http_request(url, method='HEAD'):
    (scheme, netloc, path, parms, qry, fragid) = urllib.parse.urlparse(url)
    conn = http.client.HTTPConnection(netloc)
    start = len(scheme) + len('://') + len(netloc)
    conn.request(method, url[start:])
    return conn.getresponse()


def convert_bytes(d):
    """
    Convert byte strings to unicode strings

    This function will decode byte strings into unicode
    strings. Any other data types will be left alone.

    >>> convert_bytes(None)
    >>> convert_bytes(1)
    1
    >>> convert_bytes(4711)
    4711
    >>> convert_bytes(True)
    True
    >>> convert_bytes(3.1415)
    3.1415
    >>> convert_bytes(b'Hello')
    'Hello'
    >>> convert_bytes('Hey')
    'Hey'
    """
    if d is None:
        return d
    if any(isinstance(d, t) for t in (int, int, bool, float)):
        return d
    elif not isinstance(d, str):
        return d.decode('utf-8', 'ignore')
    return d


def sanitize_filename(filename, max_length=0, use_ascii=False):
    """
    Generate a sanitized version of a filename that can
    be written on disk (i.e. remove/replace invalid
    characters and encode in the native language) and
    trim filename if greater than max_length (0 = no limit).

    If use_ascii is True, don't encode in the native language,
    but use only characters from the ASCII character set.
    """
    assert isinstance(filename, str)

    if max_length > 0 and len(filename) > max_length:
        logger.info('Limiting file/folder name "%s" to %d characters.',
                filename, max_length)
        filename = filename[:max_length]

    if use_ascii:
        filename = filename.encode('ascii', 'ignore').decode('ascii')

    filename = filename.translate(SANITIZATION_TABLE)
    filename = filename.strip('.' + string.whitespace)

    return filename


def generate_names(filename):
    basename, ext = os.path.splitext(filename)
    for i in itertools.count():
        if i:
            yield '%s (%d)%s' % (basename, i+1, ext)
        else:
            yield filename


def rename_episode_file(episode, filename): # XXX Only used by some extensions
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


def get_update_info(url='http://gpodder.org/downloads'):
    """
    Get up to date release information from gpodder.org.

    Returns a tuple: (up_to_date, latest_version, release_date, days_since)

    Example result (up to date version, 20 days after release):
        (True, '3.0.4', '2012-01-24', 20)

    Example result (outdated version, 10 days after release):
        (False, '3.0.5', '2012-02-29', 10)
    """
    data = urlopen(url).read().decode('utf-8')
    id_field_re = re.compile(r'<([a-z]*)[^>]*id="([^"]*)"[^>]*>([^<]*)</\1>')
    info = dict((m.group(2), m.group(3)) for m in id_field_re.finditer(data))

    latest_version = info['latest-version']
    release_date = info['release-date']

    release_parsed = datetime.datetime.strptime(release_date, '%Y-%m-%d')
    days_since_release = (datetime.datetime.today() - release_parsed).days

    convert = lambda s: tuple(int(x) for x in s.split('.'))
    up_to_date = (convert(gpodder.__version__) >= convert(latest_version))

    return up_to_date, latest_version, release_date, days_since_release


def run_in_background(function, daemon=False):
    logger.debug('run_in_background: %s (%s)', function, str(daemon))
    thread = threading.Thread(target=function)
    thread.setDaemon(daemon)
    thread.start()
    return thread


def linux_get_active_interfaces():
    """Get active network interfaces using 'ip link'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ip', 'link'], stdout=subprocess.PIPE)
    data, _ = process.communicate()
    for interface, _ in re.findall(r'\d+: ([^:]+):.*state (UP|UNKNOWN)', data):
        if interface != 'lo':
            yield interface


def osx_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split('\n(?!\t)', stdout, re.MULTILINE):
        b = re.match('(\\w+):.*status: active$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)

def unix_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split('\n(?!\t)', stdout, re.MULTILINE):
        b = re.match('(\\w+):.*status: active$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)


def connection_available(): # XXX Unused
    """Check if an Internet connection is available

    Returns True if a connection is available (or if there
    is no way to determine the connection). Returns False
    if no network interfaces are up (i.e. no connectivity).
    """
    try:
        if gpodder.ui.osx:
            return len(list(osx_get_active_interfaces())) > 0
        else:
            # By default, we assume we're not offline (bug 1730)
            offline = False

            if find_command('ifconfig') is not None:
                # If ifconfig is available, and it says we don't have
                # any active interfaces, assume we're offline
                if len(list(unix_get_active_interfaces())) == 0:
                    offline = True

            # If we assume we're offline, try the "ip" command as fallback
            if offline and find_command('ip') is not None:
                if len(list(linux_get_active_interfaces())) == 0:
                    offline = True
                else:
                    offline = False

            return not offline

        return False
    except Exception as e:
        logger.warn('Cannot get connection status: %s', e, exc_info=True)
        # When we can't determine the connection status, act as if we're online (bug 1730)
        return True


@contextlib.contextmanager
def update_file_safely(target_filename):
    """Update file in a safe way using atomic renames

    Example usage:

    >>> filename = tempfile.NamedTemporaryFile(delete=False).name
    >>> with update_file_safely(filename) as temp_filename:
    ...    with open(temp_filename, 'w') as fp:
    ...        fp.write('Try to write this safely')
    24
    >>> open(filename).read()
    'Try to write this safely'
    >>> with update_file_safely(filename) as temp_filename:
    ...     with open(temp_filename, 'w') as fp:
    ...         fp.write('Updated!')
    ...         raise ValueError('something bad happened')
    Traceback (most recent call last):
      ...
    ValueError: something bad happened
    >>> open(filename).read()
    'Try to write this safely'
    >>> os.remove(filename)

    Note that the temporary file will be deleted and the atomic
    rename will not take place if something in the "with"-block
    raises an exception.

    Does not take care of race conditions, as the name of the
    temporary file is predictable and not unique between different
    (possibly simultaneous) invocations of this function.
    """
    dirname = os.path.dirname(target_filename)
    basename = os.path.basename(target_filename)

    tmp_filename = os.path.join(dirname, '.tmp-' + basename)
    try:
        yield tmp_filename
    except Exception as e:
        logger.warn('Exception while atomic-saving file: %s', e, exc_info=True)
        delete_file(tmp_filename)
        raise

    os.rename(tmp_filename, target_filename)

