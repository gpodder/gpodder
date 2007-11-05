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
#  util.py -- Misc utility functions
#  Thomas Perl <thp@perli.net> 2007-08-04
#

"""Miscellaneous helper functions for gPodder

This module provides helper and utility functions for gPodder that 
are not tied to any specific part of gPodder.

"""


from gpodder.liblogger import log

import gtk

import os
import os.path
import glob

import re
import htmlentitydefs
import time
import locale

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
    
    if url.startswith( 'http://') or url.startswith( 'https://') or url.startswith( 'ftp://'):
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

    if os.path.isdir( path) and not os.path.islink( path):
        sum = os.path.getsize( path)

        for item in os.listdir( path):
            try:
                sum += calculate_size( os.path.join( path, item))
            except:
                pass

        return sum

    return 0L


def format_filesize( bytesize, use_si_units = False):
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

    return '%.2f %s' % ( used_value, used_unit )


def delete_file( path):
    """
    Tries to delete the given filename and silently 
    ignores deletion errors (if the file doesn't exist).
    Also deletes extracted cover files if they exist.
    """
    log( 'Trying to delete: %s', path)
    try:
        os.unlink( path)
        # Remove any extracted cover art that might exist
        for cover_file in glob.glob( '%s.cover.*' % ( path, )):
            os.unlink( cover_file)

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


def torrent_filename( filename):
    """
    Checks if a file is a ".torrent" file by examining its 
    contents and searching for the file name of the file 
    to be downloaded.

    Returns the name of the file the ".torrent" will download 
    or None if no filename is found (the file is no ".torrent")
    """
    if not os.path.exists( filename):
        return None

    header = open( filename).readline()
    try:
        header.index( '6:pieces')
        name_length_pos = header.index('4:name') + 6

        colon_pos = header.find( ':', name_length_pos)
        name_length = int(header[name_length_pos:colon_pos]) + 1
        name = header[(colon_pos + 1):(colon_pos + name_length)]
        return name
    except:
        return None


def file_extension_from_url( url):
    """
    Extracts the (lowercase) file name extension (with dot)
    from a URL, e.g. http://server.com/file.MP3?download=yes
    will result in the string ".mp3" being returned.
    """
    path = urlparse.urlparse( url)[2]
    filename = urllib.unquote( os.path.basename( path))
    return os.path.splitext( filename)[1].lower()


def file_type_by_extension( extension):
    """
    Tries to guess the file type by looking up the filename 
    extension from a table of known file types. Will return 
    the type as string ("audio", "video" or "torrent") or 
    None if the file type cannot be determined.
    """
    types = {
            'audio': [ 'mp3', 'ogg', 'wav', 'wma', 'aac', 'm4a' ],
            'video': [ 'mp4', 'avi', 'mpg', 'mpeg', 'm4v', 'mov', 'divx' ],
            'torrent': [ 'torrent' ],
    }

    if extension == '':
        return None

    if extension[0] == '.':
        extension = extension[1:]

    for type in types:
        if extension in types[type]:
            return type
    
    return None


def get_tree_icon( icon_name, add_bullet = False, icon_cache = None):
    """
    Loads an icon from the current icon theme at the specified
    size, suitable for display in a gtk.TreeView.

    Optionally adds a green bullet (the GTK Stock "Yes" icon)
    to the Pixbuf returned.

    If an icon_cache parameter is supplied, it has to be a
    dictionary and will be used to store generated icons. 

    On subsequent calls, icons will be loaded from cache if 
    the cache is supplied again and the icon is found in 
    the cache.
    """

    if icon_cache != None and (icon_name,add_bullet) in icon_cache:
        return icon_cache[(icon_name,add_bullet)]
    
    icon_theme = gtk.icon_theme_get_default()

    try:
        icon = icon_theme.load_icon( icon_name, 16, 0)
    except:
        log( '(get_tree_icon) Warning: Cannot load icon with name "%s", will use  default icon.', icon_name)
        icon = icon_theme.load_icon( gtk.STOCK_DIALOG_QUESTION, 16, 0)

    if add_bullet and icon:
        # We'll modify the icon, so use .copy()
        try:
            icon = icon.copy()
            emblem = icon_theme.load_icon( gtk.STOCK_YES, 10, 0)
            size = emblem.get_width()
            pos = icon.get_width() - size
            emblem.composite( icon, pos, pos, size, size, pos, pos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        except:
            log( '(get_tree_icon) Error adding emblem to icon "%s".', icon_name)

    if icon_cache != None:
        icon_cache[(icon_name,add_bullet)] = icon

    return icon


def get_first_line( s):
    """
    Returns only the first line of a string, stripped so
    that it doesn't have whitespace before or after.
    """
    return s.strip().split('\n')[0].strip()


def updated_parsed_to_rfc2822( updated_parsed):
    """
    Converts a 9-tuple from feedparser's updated_parsed 
    field to a C-locale string suitable for further use.
    """
    old_locale = locale.getlocale( locale.LC_TIME)
    locale.setlocale( locale.LC_TIME, 'C')
    result = time.strftime( '%a, %d %b %Y %H:%M:%S GMT', updated_parsed)
    locale.setlocale( locale.LC_TIME, old_locale)
    return result


def object_string_formatter( s, **kwargs):
    """
    Makes attributes of object passed in as keyword 
    arguments available as {OBJECTNAME.ATTRNAME} in 
    the passed-in string and returns a string with 
    the above arguments replaced with the attribute 
    values of the corresponding object.

    Example:

    e = Episode()
    e.title = 'Hello'
    s = '{episode.title} World'
    
    print object_string_formatter( s, episode = e)
          => 'Hello World'
    """
    result = s
    for ( key, o ) in kwargs.items():
        matches = re.findall( r'\{%s\.([^\}]+)\}' % key, s)
        for attr in matches:
            if hasattr( o, attr):
                try:
                    from_s = '{%s.%s}' % ( key, attr )
                    to_s = getattr( o, attr)
                    result = result.replace( from_s, to_s)
                except:
                    log( 'Could not replace attribute "%s" in string "%s".', attr, s)

    return result


def format_desktop_command( command, filename):
    """
    Formats a command template from the "Exec=" line of a .desktop
    file to a string that can be invoked in a shell.

    Handled format strings: %U, %u, %F, %f and a fallback that
    appends the filename as first parameter of the command.

    See http://standards.freedesktop.org/desktop-entry-spec/1.0/ar01s06.html
    """
    items = {
            '%U': 'file://%s' % filename,
            '%u': 'file://%s' % filename,
            '%F': filename,
            '%f': filename,
    }

    for key, value in items.items():
        if command.find( key) >= 0:
            return command.replace( key, value)

    return '%s "%s"' % ( command, filename )


def find_command( command):
    """
    Searches the system's PATH for a specific command that is
    executable by the user. Returns the first occurence of an
    executable binary in the PATH, or None if the command is 
    not available.
    """

    if 'PATH' not in os.environ:
        return None

    for path in os.environ['PATH'].split( os.pathsep):
        command_file = os.path.join( path, command)
        if os.path.isfile( command_file) and os.access( command_file, os.X_OK):
            return command_file
        
    return None

