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

import string
import threading
import re

class Database(object):
    UNICODE_TRANSLATE = {ord(u'ö'): u'o', ord(u'ä'): u'a', ord(u'ü'): u'u'}

    # Column names and types for the channels table
    TABLE_CHANNELS = "channels"
    SCHEMA_CHANNELS = (
            ('id', 'INTEGER PRIMARY KEY'),
            ('url', 'TEXT'), # Feed (RSS/Atom) URL of the podcast
            ('title', 'TEXT'), # Podcast name
            ('override_title', 'TEXT'), # Podcast name if user-defined
            ('link', 'TEXT'), # Website URL for the podcast
            ('description', 'TEXT'), # Description of podcast contents
            ('image', 'TEXT'), # URL to cover art for the image
            ('pubDate', 'INTEGER'), # Date and time of last feed publication
            ('sync_to_devices', 'INTEGER'), # 1 if syncing to devices is enabled, 0 otherwise
            ('device_playlist_name', 'TEXT'), # Name of the playlist on the device for syncing
            ('username', 'TEXT'), # Username for HTTP authentication (feed update + downloads)
            ('password', 'TEXT'), # Password for HTTP authentication (feed update + downloads)
            ('last_modified', 'TEXT'), # Last-modified HTTP header from last update
            ('etag', 'TEXT'), # ETag HTTP header from last update
            ('channel_is_locked', 'INTEGER'), # 1 if deletion is prevented, 0 otherwise
            ('foldername', 'TEXT'), # Folder name (basename) to put downloaded episodes
            ('auto_foldername', 'INTEGER'), # 1 if the foldername was auto-generated, 0 otherwise
            ('release_expected', 'INTEGER'), # Statistic value for when a new release is expected
            ('release_deviation', 'INTEGER'), # Deviation of the release cycle differences
            ('updated_timestamp', 'INTEGER'), # Timestamp of the last feed update
    )
    INDEX_CHANNELS = (
            ('foldername', 'UNIQUE INDEX'),
            ('url', 'UNIQUE INDEX'),
            ('sync_to_devices', 'INDEX'),
            ('title', 'INDEX'),
    )

    # Column names and types for the episodes table
    TABLE_EPISODES = 'episodes'
    SCHEMA_EPISODES = (
            ('id', 'INTEGER PRIMARY KEY'),
            ('channel_id', 'INTEGER'), # Foreign key: ID of the podcast of this episode
            ('url', 'TEXT'), # Download URL of the media file
            ('title', 'TEXT'), # Episode title
            ('length', 'INTEGER'), # File length of the media file in bytes
            ('mimetype', 'TEXT'), # Mime type of the media file
            ('guid', 'TEXT'), # GUID of the episode item
            ('description', 'TEXT'), # Longer text description
            ('link', 'TEXT'), # Website URL for the episode
            ('pubDate', 'INTEGER'), # Date and time of publication
            ('state', 'INTEGER'), # Download state (see gpodder.STATE_* constants)
            ('played', 'INTEGER'), # 1 if it's new or played, 0 otherwise
            ('locked', 'INTEGER'), # 1 if deletion is prevented, 0 otherwise
            ('filename', 'TEXT'), # Filename for the downloaded file (or NULL)
            ('auto_filename', 'INTEGER'), # 1 if the filename was auto-generated, 0 otherwise
            ('total_time', 'INTEGER'), # Length in seconds
            ('current_position', 'INTEGER'), # Current playback position
            ('current_position_updated', 'INTEGER'), # Set to NOW when updating current_position
    )
    INDEX_EPISODES = (
            ('guid', 'UNIQUE INDEX'),
            ('filename', 'UNIQUE INDEX'),
            ('channel_id', 'INDEX'),
            ('pubDate', 'INDEX'),
            ('state', 'INDEX'),
            ('played', 'INDEX'),
            ('locked', 'INDEX'),
    )

    def __init__(self, filename):
        self.database_file = filename
        self._db = None
        self.lock = threading.RLock()

    def close(self):
        self.commit()

        cur = self.cursor(lock=True)
        log('Optimizing database for faster startup.', sender=self)
        cur.execute("VACUUM")
        cur.close()
        self.lock.release()

        self._db.close()
        self._db = None

    def log(self, message, *args, **kwargs):
        try:
            message = message % args
            log('%s', message, sender=self)
        except TypeError, e:
            log('Exception in log(): %s: %s', e, message, sender=self)

    def purge(self, max_episodes, channel_id):
        """
        Deletes old episodes.  Should be called
        before adding new episodes to a channel.
        """
        cur = self.cursor(lock=True)

        self.log("purge(%s)", channel_id)
        sql = """
            DELETE FROM episodes
            WHERE channel_id = ?
            AND state <> ?
            AND id NOT IN
            (SELECT id FROM episodes WHERE channel_id = ?
            ORDER BY pubDate DESC LIMIT ?)"""
        cur.execute(sql, (channel_id, gpodder.STATE_DOWNLOADED, channel_id, max_episodes))

        cur.close()
        self.lock.release()

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
            self.log('Connected')
            self.__check_schema()
        return self._db

    def cursor(self, lock=False):
        if lock:
            self.lock.acquire()
        return self.db.cursor()

    def commit(self):
        self.lock.acquire()
        try:
            self.log("COMMIT")
            self.db.commit()
        except ProgrammingError, e:
            log('Error commiting changes: %s', e, sender=self, traceback=True)
        self.lock.release()

    def _remove_deleted_channels(self):
        """Remove deleted podcasts and episodes (upgrade from gPodder <= 2.5)

        If the database has been created with gPodder <= 2.5, it could
        be possible that podcasts have been deleted where metadata and
        episodes are kept.

        We don't support this kind of "information keeping" anymore, so
        simply go ahead and remove all podcast marked as "deleted" and
        their corresponding episodes to slim down the database.
        """
        cur = self.cursor(lock=True)
        cur.execute("PRAGMA table_info(%s)" % self.TABLE_CHANNELS)
        available = cur.fetchall()
        if available:
            ID, NAME, TYPE, NULL, DEFAULT = range(5)
            existing = set(column[NAME] for column in available)

            if 'deleted' in existing:
                cur.execute('SELECT id FROM %s WHERE deleted = ?' % self.TABLE_CHANNELS, (1,))
                channel_ids = [id for (id,) in cur]

                # Remove all deleted channels from the database
                for id in channel_ids:
                    self.log('Removing deleted channel with ID %d', id)
                    cur.execute('DELETE FROM %s WHERE id = ?' % self.TABLE_CHANNELS, (id,))
                    cur.execute('DELETE FROM %s WHERE channel_id = ?' % self.TABLE_EPISODES, (id,))
        self.lock.release()

    def __check_schema(self):
        """
        Creates all necessary tables and indexes that don't exist.
        """
        self.log('Setting up tables and views')

        cur = self.cursor(lock=True)

        # If a "deleted" column exists in the channel table, remove all
        # corresponding channels and their episodes and remove it
        self._remove_deleted_channels()

        # Create tables and possibly add newly-added columns
        self.upgrade_table(self.TABLE_CHANNELS, self.SCHEMA_CHANNELS, self.INDEX_CHANNELS)
        self.upgrade_table(self.TABLE_EPISODES, self.SCHEMA_EPISODES, self.INDEX_EPISODES)

        # Make sure deleted episodes are played, to simplify querying statistics.
        try:
            cur.execute("UPDATE episodes SET played = 1 WHERE state = ?", (gpodder.STATE_DELETED,))
        except OperationalError:
            pass

        cur.close()
        self.lock.release()

    def get_channel_count(self, id):
        """Given a channel ID, returns the statistics for it

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        cur = self.cursor(lock=True)
        cur.execute('SELECT COUNT(*), state, played FROM episodes WHERE channel_id = ? GROUP BY state, played', (id,))
        for count, state, played in cur:
            total += count
            if state == gpodder.STATE_DELETED:
                deleted += count
            elif state == gpodder.STATE_NORMAL and not played:
                new += count
            elif state == gpodder.STATE_DOWNLOADED and not played:
                downloaded += count
                unplayed += count
            elif state == gpodder.STATE_DOWNLOADED:
                downloaded += count

        cur.close()
        self.lock.release()

        return (total, deleted, new, downloaded, unplayed)

    def get_total_count(self):
        """Get statistics for episodes in all channels

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        cur = self.cursor(lock=True)
        cur.execute('SELECT COUNT(*), state, played FROM episodes GROUP BY state, played')
        for count, state, played in cur:
            total += count
            if state == gpodder.STATE_DELETED:
                deleted += count
            elif state == gpodder.STATE_NORMAL and not played:
                new += count
            elif state == gpodder.STATE_DOWNLOADED and not played:
                downloaded += count
                unplayed += count
            elif state == gpodder.STATE_DOWNLOADED:
                downloaded += count

        cur.close()
        self.lock.release()

        return (total, deleted, new, downloaded, unplayed)

    def load_channels(self, factory=None, url=None):
        """
        Returns channel descriptions as a list of dictionaries or objects,
        returned by the factory() function, which receives the dictionary
        as the only argument.
        """

        self.log("load_channels()")

        cur = self.cursor(lock=True)
        cur.execute('SELECT * FROM %s ORDER BY title COLLATE UNICODE' % self.TABLE_CHANNELS)

        result = []
        keys = list(desc[0] for desc in cur.description)
        for row in cur:
            channel = dict(zip(keys, row))

            if url is None or url == channel['url']:
                if factory is None:
                    result.append(channel)
                else:
                    result.append(factory(channel, self))

        cur.close()
        self.lock.release()

        return result

    def save_channel(self, c):
        self._save_object(c, self.TABLE_CHANNELS, self.SCHEMA_CHANNELS)

    def delete_channel(self, channel):
        assert channel.id is not None

        cur = self.cursor(lock=True)
        self.log("delete_channel(%d), %s", channel.id, channel.url)

        cur.execute("DELETE FROM channels WHERE id = ?", (channel.id, ))
        cur.execute("DELETE FROM episodes WHERE channel_id = ?", (channel.id, ))

        cur.close()
        # Commit changes
        self.db.commit()
        self.lock.release()

    def load_all_episodes(self, channel_mapping, limit=10000):
        self.log('Loading all episodes from the database')
        sql = 'SELECT * FROM %s ORDER BY pubDate DESC LIMIT ?' % (self.TABLE_EPISODES,)
        args = (limit,)
        cur = self.cursor(lock=True)
        cur.execute(sql, args)
        keys = [desc[0] for desc in cur.description]
        id_index = keys.index('channel_id')
        result = map(lambda row: channel_mapping[row[id_index]].episode_factory(dict(zip(keys, row))), cur)
        cur.close()
        self.lock.release()
        return result

    def load_episodes(self, channel, factory=lambda x: x, limit=1000, state=None):
        assert channel.id is not None

        self.log('Loading episodes for channel %d', channel.id)

        if state is None:
            sql = 'SELECT * FROM %s WHERE channel_id = ? ORDER BY pubDate DESC LIMIT ?' % (self.TABLE_EPISODES,)
            args = (channel.id, limit)
        else:
            sql = 'SELECT * FROM %s WHERE channel_id = ? AND state = ? ORDER BY pubDate DESC LIMIT ?' % (self.TABLE_EPISODES,)
            args = (channel.id, state, limit)

        cur = self.cursor(lock=True)
        cur.execute(sql, args)
        keys = [desc[0] for desc in cur.description]
        result = map(lambda row: factory(dict(zip(keys, row)), self), cur)
        cur.close()
        self.lock.release()
        return result

    def load_episode(self, id):
        """Load episode as dictionary by its id

        This will return the data for an episode as
        dictionary or None if it does not exist.
        """
        assert id is not None

        cur = self.cursor(lock=True)
        cur.execute('SELECT * from %s WHERE id = ? LIMIT 1' % (self.TABLE_EPISODES,), (id,))
        try:
            d = dict(zip((desc[0] for desc in cur.description), cur.fetchone()))
            cur.close()
            self.log('Loaded episode %d from DB', id)
            self.lock.release()
            return d
        except:
            cur.close()
            self.lock.release()
            return None

    def save_episode(self, e):
        assert e.channel_id

        if not e.guid:
            self.log('Refusing to save an episode without guid: %s', e)
            return

        self._save_object(e, self.TABLE_EPISODES, self.SCHEMA_EPISODES)

    def _save_object(self, o, table, schema):
        self.lock.acquire()
        try:
            cur = self.cursor()
            columns = [name for name, typ in schema if name != 'id']
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

    def save_downloaded_episode(self, episode):
        assert episode.id is not None

        cur = self.cursor(lock=True)
        cur.execute('UPDATE episodes SET state = ?, played = ?, length = ? WHERE id = ?', \
                (episode.state, episode.is_played, episode.length, episode.id))
        cur.close()
        self.lock.release()

    def update_episode_state(self, episode):
        assert episode.id is not None

        cur = self.cursor(lock=True)
        cur.execute('UPDATE episodes SET state = ?, played = ?, locked = ? WHERE id = ?', (episode.state, episode.is_played, episode.is_locked, episode.id))
        cur.close()
        self.lock.release()

    def update_channel_lock(self, channel):
        self.log("update_channel_lock(%s, locked=%s)", channel.url, channel.channel_is_locked)

        cur = self.cursor(lock=True)
        cur.execute("UPDATE channels SET channel_is_locked = ? WHERE url = ?", (channel.channel_is_locked, channel.url, ))
        cur.close()

        self.lock.release()

    def __get__(self, sql, params=None):
        """
        Returns the first cell of a query result, useful for COUNT()s.
        """
        cur = self.cursor(lock=True)

        self.log("__get__(): %s", sql)

        if params is None:
            cur.execute(sql)
        else:
            cur.execute(sql, params)

        row = cur.fetchone()
        cur.close()
        self.lock.release()

        if row is None:
            return None
        else:
            return row[0]

    def channel_foldername_exists(self, foldername):
        """
        Returns True if a foldername for a channel exists.
        False otherwise.
        """
        return self.__get__("SELECT id FROM channels WHERE foldername = ?", (foldername,)) is not None

    def remove_foldername_if_deleted_channel(self, foldername):
        cur = self.cursor(lock=True)
        self.log('Setting foldername=NULL for folder "%s"', foldername)
        cur.execute('UPDATE channels SET foldername=NULL ' + \
                    'WHERE foldername=? AND deleted=1', (foldername,))
        cur.close()
        self.lock.release()

    def episode_filename_exists(self, filename):
        """
        Returns True if a filename for an episode exists.
        False otherwise.
        """
        return self.__get__("SELECT id FROM episodes WHERE filename = ?", (filename,)) is not None

    def get_last_pubdate(self, channel):
        """
        Look up the highest "pubDate" value for
        all episodes of the given podcast.
        """
        return self.__get__("""
                SELECT MAX(pubDate) FROM episodes
                WHERE channel_id = ?
                """, (channel.id, ))

    def force_last_new(self, channel):
        old = self.__get__("""SELECT COUNT(*) FROM episodes WHERE channel_id = ?
            AND state IN (?, ?)""", (channel.id, gpodder.STATE_DOWNLOADED,
            gpodder.STATE_DELETED))

        cur = self.cursor(lock=True)

        self.log("force_last_new((%d)%s)", channel.id, channel.url)

        if old > 0:
            cur.execute("""
                UPDATE episodes SET played = 1 WHERE channel_id = ?
                AND played = 0 AND pubDate < (SELECT MAX(pubDate)
                FROM episodes WHERE channel_id = ? AND state IN (?, ?))""",
                (channel.id, channel.id, gpodder.STATE_DOWNLOADED,
                gpodder.STATE_DELETED, ))
        else:
            cur.execute("""
                UPDATE episodes SET played = 1 WHERE channel_id = ?
                AND pubDate <> (SELECT MAX(pubDate) FROM episodes
                WHERE channel_id = ?)""", (channel.id, channel.id, ))

        cur.close()
        self.lock.release()

    def upgrade_table(self, table_name, fields, index_list):
        """
        Creates a table or adds fields to it.
        """
        cur = self.cursor(lock=True)

        cur.execute("PRAGMA table_info(%s)" % table_name)
        available = cur.fetchall()

        if not available:
            log('Creating table %s', table_name, sender=self)
            columns = ', '.join(' '.join(f) for f in fields)
            sql = "CREATE TABLE %s (%s)" % (table_name, columns)
            cur.execute(sql)
        else:
            # Table info columns, as returned by SQLite
            ID, NAME, TYPE, NULL, DEFAULT = range(5)
            existing = set(column[NAME] for column in available)

            for field_name, field_type in fields:
                if field_name not in existing:
                    log('Adding column: %s.%s (%s)', table_name, field_name, field_type, sender=self)
                    cur.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, field_name, field_type))

        for column, typ in index_list:
            cur.execute('CREATE %s IF NOT EXISTS idx_%s ON %s (%s)' % (typ, column, table_name, column))

        self.lock.release()

    def delete_empty_episodes(self, channel_id):
        """
        Deletes episodes which haven't been downloaded.
        Currently used when a channel URL is changed.
        """
        cur = self.cursor(lock=True)
        log('Deleting old episodes from channel #%d' % channel_id, sender=self)
        cur.execute("DELETE FROM episodes WHERE channel_id = ? AND state != ?", (channel_id, gpodder.STATE_DOWNLOADED, ))
        self.lock.release()

    def delete_episode_by_guid(self, guid, channel_id):
        """
        Deletes episodes that have a specific GUID for
        a given channel. Used after feed updates for
        episodes that have disappeared from the feed.
        """
        cur = self.cursor(lock=True)
        cur.execute('DELETE FROM episodes WHERE channel_id = ? AND guid = ?', \
                (channel_id, guid))
        self.lock.release()

