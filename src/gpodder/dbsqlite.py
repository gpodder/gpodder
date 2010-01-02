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
# dbsqlite.py -- SQLite interface
# Justin Forest <justin.forest@gmail.com> 2008-06-13

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
from email.Utils import mktime_tz
from email.Utils import parsedate_tz
from email.Utils import formatdate
from threading import RLock
import string
import re

class Database(object):
    UNICODE_TRANSLATE = {ord(u'ö'): u'o', ord(u'ä'): u'a', ord(u'ü'): u'u'}

    def __init__(self, filename):
        self.database_file = filename
        self.channel_map = {}
        self._db = None
        self.lock = RLock()

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
        if False:
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

    def __check_schema(self):
        """
        Creates all necessary tables and indexes that don't exist.
        """
        self.log('Setting up tables and views')

        cur = self.cursor(lock=True)

        self.upgrade_table("channels", (
            ("id", "INTEGER PRIMARY KEY"),
            ("url", "TEXT"),
            ("title", "TEXT"),
            ("override_title", "TEXT"),
            ("link", "TEXT"),
            ("description", "TEXT"),
            ("image", "TEXT"),
            ("pubDate", "INTEGER"),
            ("sync_to_devices", "INTEGER"),
            ("device_playlist_name", "TEXT"),
            ("username", "TEXT"),
            ("password", "TEXT"),
            ("last_modified", "TEXT"),
            ("etag", "TEXT"),
            ("deleted", "INTEGER"),
            ("channel_is_locked", "INTEGER"),
            ("foldername", "TEXT"),
            ("auto_foldername", "INTEGER"),
            ("release_expected", "INTEGER"),
            ("release_deviation", "INTEGER"),
            ("updated_timestamp", "INTEGER"),
            ))

        self.upgrade_table("episodes", (
            ("id", "INTEGER PRIMARY KEY"),
            ("channel_id", "INTEGER"),
            ("url", "TEXT"),
            ("title", "TEXT"),
            ("length", "INTEGER"),
            ("mimetype", "TEXT"),
            ("guid", "TEXT"),
            ("description", "TEXT"),
            ("link", "TEXT"),
            ("pubDate", "INTEGER"),
            ("state", "INTEGER"),
            ("played", "INTEGER"),
            ("locked", "INTEGER"),
            ("filename", "TEXT"),
            ("auto_filename", "INTEGER"),
            ))

        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_foldername ON channels (foldername)""")
        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_url ON channels (url)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_sync_to_devices ON channels (sync_to_devices)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_title ON channels (title)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_deleted ON channels (deleted)""")

        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_guid ON episodes (guid)""")
        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_filename ON episodes (filename)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_channel_id ON episodes (channel_id)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_pubDate ON episodes (pubDate)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_state ON episodes (state)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_played ON episodes (played)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_locked ON episodes (locked)""")

        cur.execute("""CREATE TEMPORARY VIEW episodes_downloaded AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE state = 1 GROUP BY channel_id""")
        cur.execute("""CREATE TEMPORARY VIEW episodes_new AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE state = 0 AND played = 0 GROUP BY channel_id""")
        cur.execute("""CREATE TEMPORARY VIEW episodes_unplayed AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE played = 0 AND state = %d GROUP BY channel_id""" % gpodder.STATE_DOWNLOADED)

        # Make sure deleted episodes are played, to simplify querying statistics.
        try:
            cur.execute("UPDATE episodes SET played = 1 WHERE state = ?", (gpodder.STATE_DELETED, ))
        except OperationalError:
            pass

        cur.close()
        self.lock.release()

    def get_channel_count(self, id):
        """Given a channel ID, returns the statistics for it

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total = self.__get__('SELECT COUNT(*) FROM episodes WHERE channel_id = ?', (id,))
        deleted = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND channel_id = ?', (gpodder.STATE_DELETED, id))
        new = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND played = ? AND channel_id = ?', (gpodder.STATE_NORMAL, False, id))
        downloaded = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND channel_id = ?', (gpodder.STATE_DOWNLOADED, id))
        unplayed = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND played = ? AND channel_id = ?', (gpodder.STATE_DOWNLOADED, False, id))
        return (total, deleted, new, downloaded, unplayed)

    def get_total_count(self):
        """Get statistics for all non-deleted channels

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total = self.__get__('SELECT COUNT(*) FROM episodes WHERE channel_id IN (SELECT id FROM channels WHERE (deleted IS NULL OR deleted=0))')
        deleted = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND channel_id IN (SELECT id FROM channels WHERE (deleted IS NULL OR deleted=0))', (gpodder.STATE_DELETED,))
        new = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND played = ? AND channel_id IN (SELECT id FROM channels WHERE (deleted IS NULL OR deleted=0))', (gpodder.STATE_NORMAL, False,))
        downloaded = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND channel_id IN (SELECT id FROM channels WHERE (deleted IS NULL OR deleted=0))', (gpodder.STATE_DOWNLOADED,))
        unplayed = self.__get__('SELECT COUNT(*) FROM episodes WHERE state = ? AND played = ? AND channel_id IN (SELECT id FROM channels WHERE (deleted IS NULL OR deleted=0))', (gpodder.STATE_DOWNLOADED, False,))
        return (total, deleted, new, downloaded, unplayed)

    def load_channels(self, factory=None, url=None):
        """
        Returns channel descriptions as a list of dictionaries or objects,
        returned by the factory() function, which receives the dictionary
        as the only argument.
        """

        self.log("load_channels()")

        cur = self.cursor(lock=True)
        cur.execute("""
            SELECT
                id,
                url,
                title,
                override_title,
                link,
                description,
                image,
                pubDate,
                sync_to_devices,
                device_playlist_name,
                username,
                password,
                last_modified,
                etag,
                channel_is_locked,
                foldername,
                auto_foldername,
                release_expected,
                release_deviation,
                updated_timestamp
            FROM
                channels
            WHERE
                (deleted IS NULL OR deleted = 0)
            ORDER BY
                title COLLATE UNICODE
                """)

        stats = self.stats()

        result = []
        for row in cur.fetchall():
            channel = {
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'override_title': row[3],
                'link': row[4],
                'description': row[5],
                'image': row[6],
                'pubDate': self.__formatdate__(row[7]),
                'sync_to_devices': row[8],
                'device_playlist_name': row[9],
                'username': row[10],
                'password': row[11],
                'last_modified': row[12],
                'etag': row[13],
                'channel_is_locked': row[14],
                'foldername': row[15],
                'auto_foldername': row[16],
                'release_expected': row[17],
                'release_deviation': row[18],
                'updated_timestamp': row[19],
                }

            if row[0] in stats:
                channel['count_downloaded'] = stats[row[0]][0]
                channel['count_new'] = stats[row[0]][1]
                channel['count_unplayed'] = stats[row[0]][2]

            if url is None:
                # Maintain url/id relation for faster updates (otherwise
                # we'd need to issue an extra query to find the channel id).
                self.channel_map[channel['url']] = channel['id']

            if url is None or url == channel['url']:
                if factory is None:
                    result.append(channel)
                else:
                    result.append(factory(channel, self))

        cur.close()
        self.lock.release()

        return result

    def stats(self):
        cur = self.cursor(lock=True)
        self.log("stats()")
        cur.execute("""
            SELECT c.id, d.count, n.count, u.count
            FROM channels c
            LEFT JOIN episodes_downloaded d ON d.channel_id = c.id
            LEFT JOIN episodes_new n ON n.channel_id = c.id
            LEFT JOIN episodes_unplayed u ON u.channel_id = c.id
            WHERE c.deleted = 0
            """)

        data = {}

        for row in cur.fetchall():
            data[row[0]] = (row[1] or 0, row[2] or 0, row[3] or 0)

        cur.close()
        self.lock.release()

        return data

    def save_channel(self, c):
        if c.id is None:
            c.id = self.find_channel_id(c.url)

        cur = self.cursor(lock=True)
        self.log("save_channel((%s)%s)", c.id or "new", c.url)

        if c.id is None:
            cur.execute("INSERT INTO channels (url, title, override_title, link, description, image, pubDate, sync_to_devices, device_playlist_name, username, password, last_modified, etag, channel_is_locked, foldername, auto_foldername, release_expected, release_deviation, updated_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, c.channel_is_locked, c.foldername, c.auto_foldername, c.release_expected, c.release_deviation, c.updated_timestamp))
            self.channel_map[c.url] = cur.lastrowid
        else:
            cur.execute("UPDATE channels SET url = ?, title = ?, override_title = ?, link = ?, description = ?, image = ?, pubDate = ?, sync_to_devices = ?, device_playlist_name = ?, username = ?, password = ?, last_modified = ?, etag = ?, channel_is_locked = ?, foldername = ?, auto_foldername = ?, release_expected = ?, release_deviation = ?, updated_timestamp = ?, deleted = 0 WHERE id = ?", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, c.channel_is_locked, c.foldername, c.auto_foldername, c.release_expected, c.release_deviation, c.updated_timestamp, c.id, ))

        cur.close()
        self.lock.release()

    def delete_channel(self, channel, purge=False):
        if channel.id is None:
            channel.id = self.find_channel_id(channel.url)

        cur = self.cursor(lock=True)
        self.log("delete_channel((%d)%s), purge=%d", channel.id, channel.url, purge)

        if purge:
            cur.execute("DELETE FROM channels WHERE id = ?", (channel.id, ))
            cur.execute("DELETE FROM episodes WHERE channel_id = ?", (channel.id, ))
            if channel.url in self.channel_map:
                del self.channel_map[channel.url]
        else:
            cur.execute("UPDATE channels SET deleted = 1 WHERE id = ?", (channel.id, ))
            cur.execute("DELETE FROM episodes WHERE channel_id = ? AND state <> ?", (channel.id, gpodder.STATE_DOWNLOADED))

        cur.close()
        # Commit changes
        self.db.commit()
        self.lock.release()

    def __read_episodes(self, factory=None, where=None, params=None, commit=True):
        sql = "SELECT url, title, length, mimetype, guid, description, link, pubDate, state, played, locked, filename, auto_filename, id FROM episodes"

        if where:
            sql = "%s %s" % (sql, where)

        if params is None:
            params = ()

        cur = self.cursor(lock=True)
        cur.execute(sql, params)

        result = []
        for row in cur.fetchall():
            episode = {
                'url': row[0],
                'title': row[1],
                'length': row[2],
                'mimetype': row[3],
                'guid': row[4],
                'description': row[5],
                'link': row[6],
                'pubDate': row[7],
                'state': row[8],
                'is_played': row[9],
                'is_locked': row[10],
                'filename': row[11],
                'auto_filename': row[12],
                'id': row[13],
                }
            if episode['state'] is None:
                episode['state'] = gpodder.STATE_NORMAL
            if factory is None:
                result.append(episode)
            else:
                result.append(factory(episode, self))

        cur.close()
        self.lock.release()
        return result

    def load_episodes(self, channel, factory=None, limit=1000, state=None):
        if channel.id is None:
            channel.id = self.find_channel_id(channel.url)

        self.log("load_episodes((%d)%s)", channel.id, channel.url)

        if state is None:
            return self.__read_episodes(factory = factory, where = """
                WHERE channel_id = ? AND state = ? OR id IN
                (SELECT id FROM episodes WHERE channel_id = ?
                ORDER BY pubDate DESC LIMIT ?)
                ORDER BY pubDate DESC
                """, params = (channel.id, gpodder.STATE_DOWNLOADED, channel.id, limit, ))
        else:
            return self.__read_episodes(factory = factory, where = " WHERE channel_id = ? AND state = ? ORDER BY pubDate DESC LIMIT ?", params = (channel.id, state, limit, ))

    def load_episode(self, url, factory=None):
        self.log("load_episode(%s)", url)
        list = self.__read_episodes(factory=factory, where=' WHERE url=? LIMIT ?', params=(url, 1))
        if list:
            return list[0]
        else:
            return None

    def save_episode(self, e):
        if not e.guid:
            log('Refusing to save an episode without guid: %s', e)
            return

        self.lock.acquire()

        self.log("save_episode((%s)%s)", e.id, e.guid)

        try:
            cur = self.cursor()
            channel_id = self.find_channel_id(e.channel.url)

            if e.id is None:
                e.id = self.__get__("SELECT id FROM episodes WHERE guid = ?", (e.guid, ))
                self.log("save_episode() -- looking up id")

            if e.id is None:
                cur.execute("INSERT INTO episodes (channel_id, url, title, length, mimetype, guid, description, link, pubDate, state, played, locked, filename, auto_filename) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (channel_id, e.url, e.title, e.length, e.mimetype, e.guid, e.description, e.link, self.__mktime__(e.pubDate), e.state, e.is_played, e.is_locked, e.filename, e.auto_filename, ))
                e.id = cur.lastrowid
            else:
                cur.execute("UPDATE episodes SET title = ?, length = ?, mimetype = ?, description = ?, link = ?, pubDate = ?, state = ?, played = ?, locked = ?, filename = ?, auto_filename = ? WHERE id = ?", (e.title, e.length, e.mimetype, e.description, e.link, self.__mktime__(e.pubDate), e.state, e.is_played, e.is_locked, e.filename, e.auto_filename, e.id, ))
        except Exception, e:
            log('save_episode() failed: %s', e, sender=self)

        cur.close()
        self.lock.release()

    def mark_episode(self, url, state=None, is_played=None, is_locked=None, toggle=False):
        cur = self.cursor(lock=True)
        cur.execute("SELECT state, played, locked FROM episodes WHERE url = ?", (url, ))

        self.log("mark_episode(%s, state=%s, played=%s, locked=%s)", url, state, is_played, is_locked)

        try:
            ( cur_state, cur_played, cur_locked ) = cur.fetchone()
        except:
            # This only happens when we try to mark an unknown episode,
            # which is typical for database upgrade, so we just ignore it.
            cur.close()
            self.lock.release()
            return

        if toggle:
            if is_played:
                cur_played = not cur_played
            if is_locked:
                cur_locked = not cur_locked
        else:
            if state is not None:
                cur_state = state
            if is_played is not None:
                cur_played = is_played
            if is_locked is not None:
                cur_locked = is_locked

        cur.close()

        cur = self.cursor()
        cur.execute("UPDATE episodes SET state = ?, played = ?, locked = ? WHERE url = ?", (cur_state, cur_played, cur_locked, url, ))
        cur.close()

        self.lock.release()

    def update_channel_lock(self, channel):
        log("update_channel_lock(%s, locked=%s)", channel.url, channel.channel_is_locked, sender=self)

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

    def __mktime__(self, date):
        if isinstance(date, float) or isinstance(date, int):
            return date
        if date is None or '' == date:
            return None
        try:
            return mktime_tz(parsedate_tz(date))
        except TypeError:
            log('Could not convert "%s" to a unix timestamp.', date)
            return None

    def __formatdate__(self, date):
        try:
            return formatdate(date, localtime=1)
        except TypeError:
            log('Could not convert "%s" to a string date.', date)
            return None

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

    def find_channel_id(self, url):
        """
        Looks up the channel id in the map (which lists all undeleted
        channels), then tries to look it up in the database, including
        deleted channels.
        """
        if url in self.channel_map.keys():
            return self.channel_map[url]
        else:
            self.log("find_channel_id(%s)", url)
            return self.__get__("SELECT id FROM channels WHERE url = ?", (url, ))

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

    def upgrade_table(self, table_name, fields):
        """
        Creates a table or adds fields to it.
        """
        cur = self.cursor(lock=True)

        cur.execute("PRAGMA table_info(%s)" % table_name)
        available = cur.fetchall()

        if not len(available):
            log('Creating table %s', table_name, sender=self)
            sql = "CREATE TABLE %s (%s)" % (table_name, ", ".join([a+" "+b for (a,b) in fields]))
            cur.execute(sql)
        else:
            available = [row[1] for row in available]

            for field_name, field_type in fields:
                if field_name not in available:
                    log('Adding column %s to %s (%s)', table_name, field_name, field_type, sender=self)
                    cur.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, field_name, field_type))

        self.lock.release()

    def delete_empty_episodes(self, channel_id):
        """
        Deletes episodes which haven't been downloaded.
        Currently used when a channel URL is changed.
        """
        cur = self.cursor(lock=True)
        log('Deleting old episodes from channel #%d' % channel_id)
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

