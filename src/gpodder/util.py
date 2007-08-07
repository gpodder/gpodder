

#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, 
# MA  02110-1301, USA.
#

#
#  util.py -- Misc utility functions
#  Thomas Perl <thp@perli.net> 2007-08-04
#

"""Miscellaneous helper functions for gPodder

This module provides helper and utility functions for gPodder that 
are not tied to any specific part of gPodder.

"""


from gpodder.liblogger import log

import os
import os.path

import re
import htmlentitydefs

import urlparse
import urllib


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
        log( 'Could not create directory: %s', path)
        return False

    return True


def normalize_feed_url( url):
    """
    Converts any URL to http:// or ftp:// so that it can be 
    used with "wget". If the URL cannot be converted (invalid
    or unknown scheme), "None" is returned.
    """
    if not url or len( url) < 8:
        return None
    
    if url.startswith( 'http://') or url.startswith( 'ftp://'):
        return url

    if url.startswith( 'feed://'):
        return 'http://' + url[7:]

    return None


def username_password_from_url( url):
    """
    Returns a tuple (username,password) containing authentication
    data from the specified URL or (None,None) if no authentication
    data can be found in the URL.
    """
    (username, password) = (None, None)

    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse( url)

    if '@' in netloc:
        (username, password) = netloc.split( '@', 1)[0].split( ':', 1)
        username = urllib.unquote( username)
        password = urllib.unquote( password)

    return (username, password)


def directory_is_writable( path):
    """
    Returns True if the specified directory exists and is writable
    by the current user.
    """
    return os.path.isdir( path) and os.access( path, os.W_OK)


def calculate_size( path):
    """
    Tries to calculate the size of a directory, including any 
    subdirectories found. The returned value might not be 
    correct if the user doesn't have appropriate permissions 
    to list all subdirectories of the given path.
    """
    if os.path.dirname( path) == '/':
        return 0L

    if os.path.isfile( path):
        return os.path.getsize( path)

    if os.path.isdir( path):
        sum = os.path.getsize( path)

        for item in os.listdir( path):
            try:
                sum += calculate_size( os.path.join( path, item))
            except:
                pass

        return sum

    return 0L


def format_filesize( bytesize, method = None):
    """
    Formats the given size in bytes to be human-readable, 
    either the most appropriate form (B, KB, MB, GB) or 
    a form specified as optional second parameter (e.g. "MB").
    """
    methods = {
        'GB': 1024.0 * 1024.0 * 1024.0,
        'MB': 1024.0 * 1024.0,
        'KB': 1024.0,
        'B':  1.0
    }

    bytesize = float( bytesize)

    if method not in methods:
        method = 'B'
        for trying in ( 'KB', 'MB', 'GB' ):
            if bytesize >= methods[trying]:
                method = trying

    return '%.2f %s' % ( bytesize / methods[method], method, )


def delete_file( path):
    """
    Tries to delete the given filename and silently 
    ignores deletion errors (if the file doesn't exist).
    Also deletes extracted cover files if they exist.
    """
    log( 'Trying to delete: %s', path)
    try:
        os.unlink( path)
        # if libipodsync extracted the cover file, remove it here
        cover_path = path + '.cover.jpg'
        if os.path.isfile( cover_path):
            os.unlink( cover_path)
    except:
        pass


def remove_html_tags( html):
    """
    Remove HTML tags from a string and replace numeric and
    named entities with the corresponding character, so the 
    HTML text can be displayed in a simple text view.
    """
    # strips html from a string (fix for <description> tags containing html)
    rexp = re.compile( "<[^>]*>")
    stripstr = rexp.sub( '', html)
    # replaces numeric entities with entity names
    dict = htmlentitydefs.codepoint2name
    for key in dict.keys():
        stripstr = stripstr.replace( '&#'+str(key)+';', '&'+unicode( dict[key], 'iso-8859-1')+';')
    # strips html entities
    dict = htmlentitydefs.entitydefs
    for key in dict.keys():
        stripstr = stripstr.replace( '&'+unicode(key,'iso-8859-1')+';', unicode(dict[key], 'iso-8859-1'))
    return stripstr


