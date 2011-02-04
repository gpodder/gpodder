# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

have_sqlite = True

try:
    from sqlite3 import dbapi2 as sqlite
    from sqlite3 import OperationalError
except ImportError:
    try:
        from pysqlite2 import dbapi2 as sqlite
        from pysqlite2.dbapi2 import OperationalError
    except ImportError:
        have_sqlite = False

# TODO: show a message box
if not have_sqlite:
    print >>sys.stderr, 'Please install pysqlite2 or Python 2.5.'
    sys.exit(1)

from gpodder.liblogger import log

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
        'published',
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
    )

    def __init__(self, filename):
        self.database_file = filename
        self._db = None
        self.lock = threading.RLock()

    def close(self):
        self.commit()

        with self.lock:
            cur = self.cursor()
            log('Optimizing database for faster startup.', sender=self)
            cur.execute("VACUUM")
            cur.close()

        self._db.close()
        self._db = None

    def log(self, message, *args, **kwargs):
        try:
            message = message % args
            log('%s', message, sender=self)
        except TypeError, e:
            log('Exception in log(): %s: %s', e, message, sender=self)

    def purge(self, max_episodes, podcast_id):
        """
        Deletes old episodes.  Should be called
        before adding new episodes to a podcast.
        """
        if max_episodes == 0:
            return

        with self.lock:
            cur = self.cursor()

            self.log("purge(%s)", podcast_id)
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
            log('Error while comparing "%s" and "%s"', a, b, sender=self, traceback=True)
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

            self.log('Connected')
        return self._db

    def cursor(self):
        return self.db.cursor()

    def commit(self):
        self.lock.acquire()
        try:
            self.log("COMMIT")
            self.db.commit()
        except Exception, e:
            log('Error commiting changes: %s', e, sender=self, traceback=True)
        self.lock.release()

    def get_podcast_statistics(self, id):
        """Given a podcast ID, returns the statistics for it

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT COUNT(*), state, is_new FROM %s WHERE podcast_id = ? GROUP BY state, is_new' % self.TABLE_EPISODE, (id,))
            for count, state, is_new in cur:
                total += count
                if state == gpodder.STATE_DELETED:
                    deleted += count
                elif state == gpodder.STATE_NORMAL and is_new:
                    new += count
                elif state == gpodder.STATE_DOWNLOADED and is_new:
                    downloaded += count
                    unplayed += count
                elif state == gpodder.STATE_DOWNLOADED:
                    downloaded += count

            cur.close()

        return (total, deleted, new, downloaded, unplayed)

    def get_total_count(self):
        """Get statistics for episodes in all podcasts

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT COUNT(*), state, is_new FROM %s GROUP BY state, is_new' % self.TABLE_EPISODE)
            for count, state, is_new in cur:
                total += count
                if state == gpodder.STATE_DELETED:
                    deleted += count
                elif state == gpodder.STATE_NORMAL and is_new:
                    new += count
                elif state == gpodder.STATE_DOWNLOADED and is_new:
                    downloaded += count
                    unplayed += count
                elif state == gpodder.STATE_DOWNLOADED:
                    downloaded += count

            cur.close()

        return (total, deleted, new, downloaded, unplayed)

    def load_podcasts(self, factory=None, url=None):
        """
        Returns podcast descriptions as a list of dictionaries or objects,
        returned by the factory() function, which receives the dictionary
        as the only argument.
        """

        self.log("load_podcasts()")

        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT * FROM %s ORDER BY title COLLATE UNICODE' % self.TABLE_PODCAST)

            result = []
            keys = list(desc[0] for desc in cur.description)
            for row in cur:
                podcast = dict(zip(keys, row))

                if url is None or url == podcast['url']:
                    if factory is None:
                        result.append(podcast)
                    else:
                        result.append(factory(podcast, self))

            cur.close()

        return result

    def save_podcast(self, podcast):
        self._save_object(podcast, self.TABLE_PODCAST, self.COLUMNS_PODCAST)

    def delete_podcast(self, podcast):
        assert podcast.id

        with self.lock:
            cur = self.cursor()
            self.log("delete_podcast(%d), %s", podcast.id, podcast.url)

            cur.execute("DELETE FROM %s WHERE id = ?" % self.TABLE_PODCAST, (podcast.id, ))
            cur.execute("DELETE FROM %s WHERE podcast_id = ?" % self.TABLE_EPISODE, (podcast.id, ))

            cur.close()
            # Commit changes
            self.db.commit()

    def load_all_episodes(self, podcast_mapping, limit=10000):
        self.log('Loading all episodes from the database')
        sql = 'SELECT * FROM %s ORDER BY published DESC LIMIT ?' % (self.TABLE_EPISODE,)
        args = (limit,)
        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)
            keys = [desc[0] for desc in cur.description]
            id_index = keys.index('podcast_id')
            result = map(lambda row: podcast_mapping[row[id_index]].episode_factory(dict(zip(keys, row))), cur)
            cur.close()
        return result

    def load_episodes(self, podcast, factory=lambda x: x, limit=1000, state=None):
        assert podcast.id

        self.log('Loading episodes for podcast %d', podcast.id)

        if state is None:
            sql = 'SELECT * FROM %s WHERE podcast_id = ? ORDER BY published DESC LIMIT ?' % (self.TABLE_EPISODE,)
            args = (podcast.id, limit)
        else:
            sql = 'SELECT * FROM %s WHERE podcast_id = ? AND state = ? ORDER BY published DESC LIMIT ?' % (self.TABLE_EPISODE,)
            args = (podcast.id, state, limit)

        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)
            keys = [desc[0] for desc in cur.description]
            result = map(lambda row: factory(dict(zip(keys, row)), self), cur)
            cur.close()
        return result

    def load_single_episode(self, podcast, factory=lambda x: x, **kwargs):
        """Load one episode with keywords

        Return an episode object (created by "factory") for a
        given podcast. You can use keyword arguments to specify
        the attributes that the episode object should have.

        Returns None if the episode cannot be found.
        """
        assert podcast.id

        # Inject podcast_id into query to reduce search space
        kwargs['podcast_id'] = podcast.id

        # We need to have the keys in the same order as the values, so
        # we use items() and unzip the resulting list into two ordered lists
        keys, args = zip(*kwargs.items())

        sql = 'SELECT * FROM %s WHERE %s LIMIT 1' % (self.TABLE_EPISODE, \
                ' AND '.join('%s=?' % k for k in keys))

        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)
            keys = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            if row:
                result = factory(dict(zip(keys, row)), self)
            else:
                result = None

            cur.close()
        return result

    def load_episode(self, id):
        """Load episode as dictionary by its id

        This will return the data for an episode as
        dictionary or None if it does not exist.
        """
        assert id

        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT * from %s WHERE id = ? LIMIT 1' % (self.TABLE_EPISODE,), (id,))
            try:
                d = dict(zip((desc[0] for desc in cur.description), cur.fetchone()))
                cur.close()
                self.log('Loaded episode %d from DB', id)
                return d
            except:
                cur.close()
                return None

    def get_podcast_id_from_episode_url(self, url):
        """Return the (first) associated podcast ID given an episode URL"""
        assert url
        return self.get('SELECT podcast_id FROM %s WHERE url = ? LIMIT 1' % (self.TABLE_EPISODE,), (url,))

    def save_episode(self, episode):
        assert episode.podcast_id
        assert episode.guid
        self._save_object(episode, self.TABLE_EPISODE, self.COLUMNS_EPISODE)

    def _save_object(self, o, table, columns):
        self.lock.acquire()
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
            log('Cannot save %s to %s: %s', o, table, e, sender=self, traceback=True)

        cur.close()
        self.lock.release()

    def update_episode_state(self, episode):
        assert episode.id is not None

        with self.lock:
            cur = self.cursor()
            cur.execute('UPDATE %s SET state = ?, is_new = ?, archive = ? WHERE id = ?' % (self.TABLE_EPISODE,), (episode.state, episode.is_new, episode.archive, episode.id))
            cur.close()

    def get(self, sql, params=None):
        """
        Returns the first cell of a query result, useful for COUNT()s.
        """
        with self.lock:
            cur = self.cursor()

            self.log("get(): %s", sql)

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

    def episode_filename_exists(self, filename):
        """
        Returns True if a filename for an episode exists.
        False otherwise.
        """
        return self.get("SELECT id FROM %s WHERE download_filename = ?" % self.TABLE_EPISODE, (filename,)) is not None

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

