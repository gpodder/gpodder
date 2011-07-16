# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
# dbsqlite.py -- SQLite persistence layer for gPodder
#
# 2008-06-13 Justin Forest <justin.forest@gmail.com>
# 2010-04-24 Thomas Perl <thp@gpodder.org>
#

from __future__ import with_statement

import gpodder
_ = gpodder.gettext

import sys

from sqlite3 import dbapi2 as sqlite

import logging
logger = logging.getLogger(__name__)

from gpodder import schema

import threading
import re

class Database(object):
    UNICODE_TRANSLATE = {ord(u'ö'): u'o', ord(u'ä'): u'a', ord(u'ü'): u'u'}

    # Column names, types, required and default values for the podcasts table
    TABLE_PODCAST = 'podcast'
    COLUMNS_PODCAST = (
        'title',
        'url',
        'link',
        'description',
        'cover_url',
        'auth_username',
        'auth_password',
        'http_last_modified',
        'http_etag',
        'auto_archive_episodes',
        'download_folder',
        'pause_subscription',
    )

    # Column names and types for the episodes table
    TABLE_EPISODE = 'episode'
    COLUMNS_EPISODE = (
        'podcast_id',
        'title',
        'description',
        'url',
        'published',
        'guid',
        'link',
        'file_size',
        'mime_type',
        'state',
        'is_new',
        'archive',
        'download_filename',
        'total_time',
        'current_position',
        'current_position_updated',
        'last_playback',
    )

    def __init__(self, filename):
        self.database_file = filename
        self._db = None
        self.lock = threading.RLock()

    def close(self):
        self.commit()

        with self.lock:
            cur = self.cursor()
            cur.execute("VACUUM")
            cur.close()

        self._db.close()
        self._db = None

    def purge(self, max_episodes, podcast_id):
        """
        Deletes old episodes.  Should be called
        before adding new episodes to a podcast.
        """
        if max_episodes == 0:
            return

        with self.lock:
            cur = self.cursor()

            logger.debug('Purge requested for podcast %d', podcast_id)
            sql = """
                DELETE FROM %s
                WHERE podcast_id = ?
                AND state <> ?
                AND id NOT IN
                (SELECT id FROM %s WHERE podcast_id = ?
                ORDER BY published DESC LIMIT ?)""" % (self.TABLE_EPISODE, self.TABLE_EPISODE)
            cur.execute(sql, (podcast_id, gpodder.STATE_DOWNLOADED, podcast_id, max_episodes))

            cur.close()

    def db_sort_cmp(self, a, b):
        """
        Compare two strings for sorting, including removing
        a possible "The " prefix and converting umlauts to
        normal characters so they can be sorted correctly.
        (i.e. "Ö1" should not appear at the end of the list)
        """
        try:
            a = a.decode('utf-8', 'ignore').lower()
            a = re.sub('^the ', '', a)
            a = a.translate(self.UNICODE_TRANSLATE)
            b = b.decode('utf-8', 'ignore').lower()
            b = re.sub('^the ', '', b)
            b = b.translate(self.UNICODE_TRANSLATE)
            return cmp(a, b)
        except:
            logger.warn('Error comparing %s <=> %s', a, b, exc_info=True)
            a = re.sub('^the ', '', a.lower())
            b = re.sub('^the ', '', b.lower())
            return cmp(a, b)

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite.connect(self.database_file, check_same_thread=False)
            self._db.text_factory = str
            self._db.create_collation("UNICODE", self.db_sort_cmp)

            # Check schema version, upgrade if necessary
            schema.upgrade(self._db)

            logger.debug('Database opened.')
        return self._db

    def cursor(self):
        return self.db.cursor()

    def commit(self):
        with self.lock:
            try:
                logger.debug('Commit.')
                self.db.commit()
            except Exception, e:
                logger.error('Cannot commit: %s', e, exc_info=True)

    def get_content_types(self, id):
        """Given a podcast ID, returns the content types"""
        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT DISTINCT mime_type AS mime_type FROM %s WHERE podcast_id = ?' % self.TABLE_EPISODE, (id,))
            for (mime_type,) in cur:
                yield mime_type
            cur.close()

    def get_podcast_statistics(self, podcast_id=None):
        """Given a podcast ID, returns the statistics for it

        If the podcast_id is omitted (using the default value), the
        statistics will be calculated over all podcasts.

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        with self.lock:
            cur = self.cursor()
            if podcast_id is not None:
                cur.execute('SELECT COUNT(*), state, is_new FROM %s WHERE podcast_id = ? GROUP BY state, is_new' % self.TABLE_EPISODE, (podcast_id,))
            else:
                cur.execute('SELECT COUNT(*), state, is_new FROM %s GROUP BY state, is_new' % self.TABLE_EPISODE)
            for count, state, is_new in cur:
                total += count
                if state == gpodder.STATE_DELETED:
                    deleted += count
                elif state == gpodder.STATE_NORMAL and is_new:
                    new += count
                elif state == gpodder.STATE_DOWNLOADED:
                    downloaded += count
                    if is_new:
                        unplayed += count

            cur.close()

        return (total, deleted, new, downloaded, unplayed)

    def load_podcasts(self, factory, cache_lookup):
        """
        Returns podcast descriptions as a list of dictionaries or objects,
        returned by the factory() function, which receives the dictionary
        as the only argument.

        The cache_lookup function takes a podcast ID and should return the
        podcast object in case it is cached already in memory.
        """

        logger.debug('load_podcasts')

        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT * FROM %s ORDER BY title COLLATE UNICODE' % self.TABLE_PODCAST)

            result = []
            keys = [desc[0] for desc in cur.description]
            id_index = keys.index('id')
            def make_podcast(row):
                o = cache_lookup(row[id_index])
                if o is None:
                    o = factory(dict(zip(keys, row)), self)
                    # TODO: save in cache!
                else:
                    logger.debug('Cache hit: podcast %d', o.id)
                return o

            result = map(make_podcast, cur)
            cur.close()

        return result

    def delete_podcast(self, podcast):
        assert podcast.id

        with self.lock:
            cur = self.cursor()
            logger.debug('delete_podcast: %d (%s)', podcast.id, podcast.url)

            cur.execute("DELETE FROM %s WHERE id = ?" % self.TABLE_PODCAST, (podcast.id, ))
            cur.execute("DELETE FROM %s WHERE podcast_id = ?" % self.TABLE_EPISODE, (podcast.id, ))

            cur.close()
            # Commit changes
            self.db.commit()
            # TODO: podcast.id -> remove from cache!

    def load_episodes(self, podcast, factory, cache_lookup):
        assert podcast.id
        limit = 1000

        logger.info('Loading episodes for podcast %d', podcast.id)

        sql = 'SELECT * FROM %s WHERE podcast_id = ? ORDER BY published DESC LIMIT ?' % (self.TABLE_EPISODE,)
        args = (podcast.id, limit)

        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)
            keys = [desc[0] for desc in cur.description]
            id_index = keys.index('id')
            def make_episode(row):
                o = cache_lookup(row[id_index])
                if o is None:
                    o = factory(dict(zip(keys, row)))
                    # TODO: save in cache!
                else:
                    logger.debug('Cache hit: episode %d', o.id)
                return o

            result = map(make_episode, cur)
            cur.close()
        return result

    def get_podcast_id_from_episode_url(self, url):
        """Return the (first) associated podcast ID given an episode URL"""
        assert url
        return self.get('SELECT podcast_id FROM %s WHERE url = ? LIMIT 1' % (self.TABLE_EPISODE,), (url,))

    def save_podcast(self, podcast):
        self._save_object(podcast, self.TABLE_PODCAST, self.COLUMNS_PODCAST)

    def save_episode(self, episode):
        assert episode.podcast_id
        assert episode.guid
        self._save_object(episode, self.TABLE_EPISODE, self.COLUMNS_EPISODE)

    def _save_object(self, o, table, columns):
        with self.lock:
            try:
                cur = self.cursor()
                values = [getattr(o, name) for name in columns]

                if o.id is None:
                    qmarks = ', '.join('?'*len(columns))
                    sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, ', '.join(columns), qmarks)
                    cur.execute(sql, values)
                    o.id = cur.lastrowid
                else:
                    qmarks = ', '.join('%s = ?' % name for name in columns)
                    values.append(o.id)
                    sql = 'UPDATE %s SET %s WHERE id = ?' % (table, qmarks)
                    cur.execute(sql, values)
            except Exception, e:
                logger.error('Cannot save %s: %s', o, e, exc_info=True)

            cur.close()
            # TODO: o -> into cache!

    def get(self, sql, params=None):
        """
        Returns the first cell of a query result, useful for COUNT()s.
        """
        with self.lock:
            cur = self.cursor()

            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, params)

            row = cur.fetchone()
            cur.close()

        if row is None:
            return None
        else:
            return row[0]

    def podcast_download_folder_exists(self, foldername):
        """
        Returns True if a foldername for a channel exists.
        False otherwise.
        """
        return self.get("SELECT id FROM %s WHERE download_folder = ?" % self.TABLE_PODCAST, (foldername,)) is not None

    def episode_filename_exists(self, podcast_id, filename):
        """
        Returns True if a filename for an episode exists.
        False otherwise.
        """
        return self.get("SELECT id FROM %s WHERE podcast_id = ? AND download_filename = ?" % self.TABLE_EPISODE, (podcast_id, filename,)) is not None

    def get_last_published(self, podcast):
        """
        Look up the most recent publish date of a podcast.
        """
        return self.get('SELECT MAX(published) FROM %s WHERE podcast_id = ?' % self.TABLE_EPISODE, (podcast.id,))

    def delete_episode_by_guid(self, guid, podcast_id):
        """
        Deletes episodes that have a specific GUID for
        a given channel. Used after feed updates for
        episodes that have disappeared from the feed.
        """
        with self.lock:
            cur = self.cursor()
            cur.execute('DELETE FROM %s WHERE podcast_id = ? AND guid = ?' % self.TABLE_EPISODE, \
                    (podcast_id, guid))
            # TODO: Delete episode from cache

