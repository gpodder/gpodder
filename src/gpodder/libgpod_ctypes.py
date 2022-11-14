#
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2022 The gPodder Team
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
# libgpod_ctypes: Minimalistic ctypes-based bindings for libgpod
# (Just enough coverage to get podcast syncing working again...)
# Thomas Perl <m@thp.io>, May 2022
#


import ctypes
import logging
import os

logger = logging.getLogger(__name__)


# libgpod, for iTunesDB access
libgpod = ctypes.CDLL('libgpod.so.4')

# glib, for g_strdup() and g_free()
libglib = ctypes.CDLL('libglib-2.0.so.0')


# glib/gtypes.h: typedef gint   gboolean;
gboolean = ctypes.c_int

# glib/gstrfuncs.h: gchar *g_strdup(const gchar *str);
libglib.g_strdup.argtypes = (ctypes.c_char_p,)
# Note: This MUST be c_void_p, so that the glib-allocated buffer will
# be preserved when assigning to track member variables. The reason
# for this is that Python ctypes tries to be helpful and converts a
# c_char_p restype to a Python bytes object, which will be different
# from the memory returned by g_strdup(). For track properties, the
# values will be free'd indirectly by itdb_free() later.
libglib.g_strdup.restype = ctypes.c_void_p

# glib/gmem.h: void g_free(gpointer mem);
libglib.g_free.argtypes = (ctypes.c_void_p,)
libglib.g_free.restype = None

# ctypes.c_time_t will be available in Python 3.12 onwards
# See also: https://github.com/python/cpython/pull/92870
if hasattr(ctypes, 'c_time_t'):
    time_t = ctypes.c_time_t
else:
    # See also: https://github.com/python/cpython/issues/92869
    if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_int64):
        time_t = ctypes.c_int64
    else:
        # On 32-bit systems, time_t is historically 32-bit, but due to Y2K38
        # there have been efforts to establish 64-bit time_t on 32-bit Linux:
        # https://linux.slashdot.org/story/20/02/15/0247201/linux-is-ready-for-the-end-of-time
        # https://www.gnu.org/software/libc/manual/html_node/64_002dbit-time-symbol-handling.html
        logger.info('libgpod may cause issues if time_t is 64-bit on your 32-bit system.')
        time_t = ctypes.c_int32


# glib/glist.h: struct _GList
class GList(ctypes.Structure):
    ...


GList._fields_ = [
    ('data', ctypes.c_void_p),
    ('next', ctypes.POINTER(GList)),
    ('prev', ctypes.POINTER(GList)),
]


# gpod/itdb.h
class Itdb_iTunesDB(ctypes.Structure):
    _fields_ = [
        ('tracks', ctypes.POINTER(GList)),
        # ...
    ]


# gpod/itdb.h: struct _Itdb_Playlist
class Itdb_Playlist(ctypes.Structure):
    _fields_ = [
        ('itdb', ctypes.POINTER(Itdb_iTunesDB)),
        ('name', ctypes.c_char_p),
        ('type', ctypes.c_uint8),
        ('flag1', ctypes.c_uint8),
        ('flag2', ctypes.c_uint8),
        ('flag3', ctypes.c_uint8),
        ('num', ctypes.c_int),
        ('members', ctypes.POINTER(GList)),
        # ...
    ]


# gpod/itdb.h
class Itdb_Chapterdata(ctypes.Structure):
    ...


# gpod/itdb.h
class Itdb_Track(ctypes.Structure):
    _fields_ = [
        ('itdb', ctypes.POINTER(Itdb_iTunesDB)),
        ('title', ctypes.c_char_p),
        ('ipod_path', ctypes.c_char_p),
        ('album', ctypes.c_char_p),
        ('artist', ctypes.c_char_p),
        ('genre', ctypes.c_char_p),
        ('filetype', ctypes.c_char_p),
        ('comment', ctypes.c_char_p),
        ('category', ctypes.c_char_p),
        ('composer', ctypes.c_char_p),
        ('grouping', ctypes.c_char_p),
        ('description', ctypes.c_char_p),
        ('podcasturl', ctypes.c_char_p),
        ('podcastrss', ctypes.c_char_p),
        ('chapterdata', ctypes.POINTER(Itdb_Chapterdata)),
        ('subtitle', ctypes.c_char_p),
        ('tvshow', ctypes.c_char_p),
        ('tvepisode', ctypes.c_char_p),
        ('tvnetwork', ctypes.c_char_p),
        ('albumartist', ctypes.c_char_p),
        ('keywords', ctypes.c_char_p),
        ('sort_artist', ctypes.c_char_p),
        ('sort_title', ctypes.c_char_p),
        ('sort_album', ctypes.c_char_p),
        ('sort_albumartist', ctypes.c_char_p),
        ('sort_composer', ctypes.c_char_p),
        ('sort_tvshow', ctypes.c_char_p),
        ('id', ctypes.c_uint32),
        ('size', ctypes.c_uint32),
        ('tracklen', ctypes.c_int32),
        ('cd_nr', ctypes.c_int32),
        ('cds', ctypes.c_int32),
        ('track_nr', ctypes.c_int32),
        ('bitrate', ctypes.c_int32),
        ('samplerate', ctypes.c_uint16),
        ('samplerate_low', ctypes.c_uint16),
        ('year', ctypes.c_int32),
        ('volume', ctypes.c_int32),
        ('soundcheck', ctypes.c_uint32),
        ('soundcheck', ctypes.c_uint32),
        ('time_added', time_t),
        ('time_modified', time_t),
        ('time_played', time_t),
        ('bookmark_time', ctypes.c_uint32),
        ('rating', ctypes.c_uint32),
        ('playcount', ctypes.c_uint32),
        ('playcount2', ctypes.c_uint32),
        ('recent_playcount', ctypes.c_uint32),
        ('transferred', gboolean),
        ('BPM', ctypes.c_int16),
        ('app_rating', ctypes.c_uint8),
        ('type1', ctypes.c_uint8),
        ('type2', ctypes.c_uint8),
        ('compilation', ctypes.c_uint8),
        ('starttime', ctypes.c_uint32),
        ('stoptime', ctypes.c_uint32),
        ('checked', ctypes.c_uint8),
        ('dbid', ctypes.c_uint64),
        ('drm_userid', ctypes.c_uint32),
        ('visible', ctypes.c_uint32),
        ('filetype_marker', ctypes.c_uint32),
        ('artwork_count', ctypes.c_uint16),
        ('artwork_size', ctypes.c_uint32),
        ('samplerate2', ctypes.c_float),
        ('unk126', ctypes.c_uint16),
        ('unk132', ctypes.c_uint32),
        ('time_released', time_t),
        ('unk144', ctypes.c_uint16),
        ('explicit_flag', ctypes.c_uint16),
        ('unk148', ctypes.c_uint32),
        ('unk152', ctypes.c_uint32),
        ('skipcount', ctypes.c_uint32),
        ('recent_skipcount', ctypes.c_uint32),
        ('last_skipped', ctypes.c_uint32),
        ('has_artwork', ctypes.c_uint8),
        ('skip_when_shuffling', ctypes.c_uint8),
        ('remember_playback_position', ctypes.c_uint8),
        ('flag4', ctypes.c_uint8),
        ('dbid2', ctypes.c_uint64),
        ('lyrics_flag', ctypes.c_uint8),
        ('movie_flag', ctypes.c_uint8),
        ('mark_unplayed', ctypes.c_uint8),
        ('unk179', ctypes.c_uint8),
        ('unk180', ctypes.c_uint32),
        ('pregap', ctypes.c_uint32),
        ('samplecount', ctypes.c_uint64),
        ('unk196', ctypes.c_uint32),
        ('postgap', ctypes.c_uint32),
        ('unk204', ctypes.c_uint32),
        ('mediatype', ctypes.c_uint32),
        # ...
    ]


# gpod/itdb.h: Itdb_iTunesDB *itdb_parse (const gchar *mp, GError **error);
libgpod.itdb_parse.argtypes = (ctypes.c_char_p, ctypes.c_void_p)
libgpod.itdb_parse.restype = ctypes.POINTER(Itdb_iTunesDB)

# gpod/itdb.h: Itdb_Playlist *itdb_playlist_podcasts (Itdb_iTunesDB *itdb);
libgpod.itdb_playlist_podcasts.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_playlist_podcasts.restype = ctypes.POINTER(Itdb_Playlist)

# gpod/itdb.h: Itdb_Playlist *itdb_playlist_mpl (Itdb_iTunesDB *itdb);
libgpod.itdb_playlist_mpl.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_playlist_mpl.restype = ctypes.POINTER(Itdb_Playlist)

# gpod/itdb.h: gboolean itdb_write (Itdb_iTunesDB *itdb, GError **error);
libgpod.itdb_write.argtypes = (ctypes.POINTER(Itdb_iTunesDB), ctypes.c_void_p)
libgpod.itdb_write.restype = gboolean

# gpod/itdb.h: guint32 itdb_playlist_tracks_number (Itdb_Playlist *pl);
libgpod.itdb_playlist_tracks_number.argtypes = (ctypes.POINTER(Itdb_Playlist),)
libgpod.itdb_playlist_tracks_number.restype = ctypes.c_uint32

# gpod/itdb.h: gchar *itdb_filename_on_ipod (Itdb_Track *track);
libgpod.itdb_filename_on_ipod.argtypes = (ctypes.POINTER(Itdb_Track),)
# Needs to be c_void_p, because the returned pointer-to-memory must be free'd with g_free() after use.
libgpod.itdb_filename_on_ipod.restype = ctypes.c_void_p

# gpod/itdb.h: Itdb_Track *itdb_track_new (void);
libgpod.itdb_track_new.argtypes = ()
libgpod.itdb_track_new.restype = ctypes.POINTER(Itdb_Track)

# gpod/itdb.h: void itdb_track_add (Itdb_iTunesDB *itdb, Itdb_Track *track, gint32 pos);
libgpod.itdb_track_add.argtypes = (ctypes.POINTER(Itdb_iTunesDB), ctypes.POINTER(Itdb_Track), ctypes.c_int32)
libgpod.itdb_track_add.restype = None

# gpod/itdb.h: void itdb_playlist_add_track (Itdb_Playlist *pl, Itdb_Track *track, gint32 pos);
libgpod.itdb_playlist_add_track.argtypes = (ctypes.POINTER(Itdb_Playlist), ctypes.POINTER(Itdb_Track), ctypes.c_int32)
libgpod.itdb_playlist_add_track.restype = None

# gpod/itdb.h: gboolean itdb_cp_track_to_ipod (Itdb_Track *track, const gchar *filename, GError **error);
libgpod.itdb_cp_track_to_ipod.argtypes = (ctypes.POINTER(Itdb_Track), ctypes.c_char_p, ctypes.c_void_p)
libgpod.itdb_cp_track_to_ipod.restype = gboolean

# gpod/itdb.h: time_t itdb_time_host_to_mac (time_t time);
libgpod.itdb_time_host_to_mac.argtypes = (time_t,)
libgpod.itdb_time_host_to_mac.restype = time_t

# gpod/itdb.h: void itdb_playlist_remove_track (Itdb_Playlist *pl, Itdb_Track *track);
libgpod.itdb_playlist_remove_track.argtypes = (ctypes.POINTER(Itdb_Playlist), ctypes.POINTER(Itdb_Track))
libgpod.itdb_playlist_remove_track.restype = None

# gpod/itdb.h: void itdb_track_remove (Itdb_Track *track);
libgpod.itdb_track_remove.argtypes = (ctypes.POINTER(Itdb_Track),)
libgpod.itdb_track_remove.restype = None

# gpod/itdb.h: void itdb_free (Itdb_iTunesDB *itdb);
libgpod.itdb_free.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_free.restype = None


# gpod/itdb.h
ITDB_MEDIATYPE_AUDIO = (1 << 0)
ITDB_MEDIATYPE_MOVIE = (1 << 1)
ITDB_MEDIATYPE_PODCAST = (1 << 2)
ITDB_MEDIATYPE_VIDEO_PODCAST = (ITDB_MEDIATYPE_MOVIE | ITDB_MEDIATYPE_PODCAST)


def glist_foreach(ptr_to_glist, item_type):
    cur = ptr_to_glist
    while cur:
        yield ctypes.cast(cur[0].data, item_type)
        if not cur[0].next:
            break
        cur = cur[0].next


class iPodTrack(object):
    def __init__(self, db, track):
        self.db = db
        self.track = track

        self.episode_title = track[0].title.decode()
        self.podcast_title = track[0].album.decode()

        self.podcast_url = track[0].podcasturl.decode()
        self.podcast_rss = track[0].podcastrss.decode()

        self.playcount = track[0].playcount
        self.bookmark_time = track[0].bookmark_time

        # This returns a newly-allocated string, so we have to juggle the memory
        # around a bit and take a copy of the string before free'ing it again.
        filename_ptr = libgpod.itdb_filename_on_ipod(track)
        if filename_ptr:
            self.filename_on_ipod = ctypes.string_at(filename_ptr).decode()
            libglib.g_free(filename_ptr)
        else:
            self.filename_on_ipod = None

    def __repr__(self):
        return 'iPodTrack(episode={}, podcast={})'.format(self.episode_title, self.podcast_title)

    def initialize_bookmark(self, is_new, bookmark_time):
        self.track[0].mark_unplayed = 0x02 if is_new else 0x01
        self.track[0].bookmark_time = int(bookmark_time)

    def remove_from_device(self):
        libgpod.itdb_playlist_remove_track(self.db.podcasts_playlist, self.track)
        libgpod.itdb_playlist_remove_track(self.db.master_playlist, self.track)

        # This frees the memory pointed-to by the track object
        libgpod.itdb_track_remove(self.track)

        self.track = None

        # Don't forget to write the database on close
        self.db.modified = True

        if self.filename_on_ipod is not None:
            try:
                os.unlink(self.filename_on_ipod)
            except Exception as e:
                logger.info('Could not delete podcast file from iPod', exc_info=True)


class iPodDatabase(object):
    def __init__(self, mountpoint):
        self.mountpoint = mountpoint
        self.itdb = libgpod.itdb_parse(mountpoint.encode(), None)

        if not self.itdb:
            raise ValueError('iTunesDB not found at {}'.format(self.mountpoint))

        logger.info('iTunesDB: %s', self.itdb)

        self.modified = False

        self.podcasts_playlist = libgpod.itdb_playlist_podcasts(self.itdb)
        self.master_playlist = libgpod.itdb_playlist_mpl(self.itdb)

        self.tracks = [iPodTrack(self, track)
                       for track in glist_foreach(self.podcasts_playlist[0].members, ctypes.POINTER(Itdb_Track))]

    def get_podcast_tracks(self):
        return self.tracks

    def add_track(self, filename, episode_title, podcast_title, description, podcast_url, podcast_rss,
            published_timestamp, track_length, is_audio):
        track = libgpod.itdb_track_new()

        track[0].title = libglib.g_strdup(episode_title.encode())
        track[0].album = libglib.g_strdup(podcast_title.encode())
        track[0].artist = libglib.g_strdup(podcast_title.encode())
        track[0].description = libglib.g_strdup(description.encode())
        track[0].podcasturl = libglib.g_strdup(podcast_url.encode())
        track[0].podcastrss = libglib.g_strdup(podcast_rss.encode())
        track[0].tracklen = track_length
        track[0].size = os.path.getsize(filename)
        track[0].time_released = libgpod.itdb_time_host_to_mac(published_timestamp)

        if is_audio:
            track[0].filetype = libglib.g_strdup(b'mp3')
            track[0].mediatype = ITDB_MEDIATYPE_PODCAST
        else:
            track[0].filetype = libglib.g_strdup(b'm4v')
            track[0].mediatype = ITDB_MEDIATYPE_VIDEO_PODCAST

        # Start at the beginning, and add "unplayed" bullet
        track[0].bookmark_time = 0
        track[0].mark_unplayed = 0x02

        # from set_podcast_flags()
        track[0].remember_playback_position = 0x01
        track[0].skip_when_shuffling = 0x01
        track[0].flag1 = 0x02
        track[0].flag2 = 0x01
        track[0].flag3 = 0x01
        track[0].flag4 = 0x01

        libgpod.itdb_track_add(self.itdb, track, -1)

        libgpod.itdb_playlist_add_track(self.podcasts_playlist, track, -1)
        libgpod.itdb_playlist_add_track(self.master_playlist, track, -1)

        copied = libgpod.itdb_cp_track_to_ipod(track, filename.encode(), None)
        logger.info('Copy result: %r', copied)
        self.modified = True

        self.tracks.append(iPodTrack(self, track))
        return self.tracks[-1]

    def __del__(self):
        # If we hit the finalizer without closing the iTunesDB properly,
        # just free the memory, but don't write out any modifications.
        self.close(write=False)

    def close(self, write=True):
        if self.itdb:
            if self.modified and write:
                result = libgpod.itdb_write(self.itdb, None)
                logger.info('Close result: %r', result)
                self.modified = False

            libgpod.itdb_free(self.itdb)
            self.itdb = None


if __name__ == '__main__':
    import argparse
    import textwrap

    parser = argparse.ArgumentParser(description='Dump podcasts in iTunesDB via libgpod')
    parser.add_argument('mountpoint', type=str, help='Path to mounted iPod storage')

    args = parser.parse_args()

    ipod = iPodDatabase(args.mountpoint)

    for track in ipod.get_podcast_tracks():
        print(textwrap.dedent(f"""
        Episode:     {track.episode_title}
        Podcast:     {track.podcast_title}
        Episode URL: {track.podcast_url}
        Podcast URL: {track.podcast_rss}
        Play count:  {track.playcount}
        Bookmark:    {track.bookmark_time/1000:.0f} seconds
        Filename:    {track.filename_on_ipod}
        """).rstrip())

    ipod.close()
