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
#  libtagupdate.py -- tag updating/writing library
#  thomas perl <thp@perli.net>   20070315
#
#


# for ogg/vorbis (vorbiscomment utility)
import popen2

# for logging
from liblogger import log

# for mp3 files
has_eyed3 = True
try:
    import eyeD3
except:
    log('(tagupdate) eyed3 not found -- tag update disabled')
    has_eyed3 = False

# Values that we want to have for our tags
tags_keys = ['artist', 'title', 'album', 'genre']

# do we provide tagging functions to the user?
def tagging_supported():
    global has_eyed3
    return has_eyed3


tag_update_methods = {}
tag_get_methods = {}

def update_metadata_on_file( filename, **metadata):
    global tag_update_methods

    ext = filename[-3:]
    if ext in tag_update_methods:
        log('Updating tag for %s', filename)
        return tag_update_methods[ext]( filename, **metadata)

    log('Do not know how to update file extension %s :/', ext)
    return False


def update_tag_ogg( filename, **metadata):
    data = '\n'.join( [ '%s=%s' % ( i.upper(), metadata[i] ) for i in metadata ] + [''])

    p = popen2.Popen3('vorbiscomment -w "%s"' % filename)

    writer = p.tochild
    writer.write(data)
    writer.close()

    result = p.wait() == 0

    if not result:
        log('Error while running vorbiscomment. Is it installed?! (vorbis-tools)')

    return result

tag_update_methods['ogg'] = update_tag_ogg


def update_tag_mp3( filename, **metadata):
    if not has_eyed3:
        log('eyeD3 not found -> please install. no tags have been updated.')
        return False

    tag = eyeD3.tag.Tag( fileName = filename)
    tag.remove( eyeD3.tag.ID3_ANY_VERSION)
    tag.setVersion( eyeD3.tag.ID3_ANY_VERSION)

    for key in metadata:
        if key.lower() == 'artist':
            tag.setArtist( metadata[key])
            # Set "album" info from artist name if it is not available
            if 'album' not in metadata and tag.getAlbum().strip() == '':
                log('(tagupdate) No album information - using artist')
                tag.setAlbum(metadata[key])
        elif key.lower() == 'title':
            tag.setTitle( metadata[key])
        elif key.lower() == 'album':
            tag.setAlbum( metadata[key])
        elif key.lower() == 'genre':
            tag.setGenre(metadata[key])

    return tag.update( eyeD3.tag.ID3_V2) == 1 and tag.update( eyeD3.tag.ID3_V1) == 1

tag_update_methods['mp3'] = update_tag_mp3


def get_tags_from_file(filename):
    global tag_get_methods, tags_keys

    ext = filename[-3:]
    if ext in tag_get_methods:
        log('Reading tags from %s', filename)
        return tag_get_methods[ext](filename)

    log('Do not know how to read file extension %s :/', ext)
    return dict(map(lambda key: (key, ''), tags_keys))



def get_tags_ogg(filename):
    global tags_keys

    p = popen2.Popen3('vorbiscomment -l "%s"' % filename)
    reader = p.fromchild
    lines = reader.readlines()
    reader.close()
    result = (p.wait() == 0)

    tags = dict(map(lambda key: (key, ''), tags_keys))

    if not result:
        log('Error while running vorbiscomment. Is it installed?! (vorbis-tools)')
    else:
        for line in lines:
            (key, value) = line.split('=', 1)
            key = key.lower()
            if key in tags:
                tags[key] = value

    return tags

tag_get_methods['ogg'] = get_tags_ogg


def get_tags_mp3(filename):
    global tags_keys

    if not has_eyed3:
        log('eyeD3 not found -> please install. Could not read tag.')
        return dict(map(lambda key: (key, ''), tags_keys))

    tag = eyeD3.Tag()
    tag.link(filename)

    return {
            'artist': tag.getArtist(),
            'title': tag.getTitle(),
            'album': tag.getAlbum(),
            'genre': tag.getGenre()
    }

tag_get_methods['mp3'] = get_tags_mp3

