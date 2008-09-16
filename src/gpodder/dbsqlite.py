# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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

have_sqlite = True

try:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        have_sqlite = False

# TODO: show a message box
if not have_sqlite:
    print "Please install pysqlite2 or upgrade to Python 2.5."
    import sys
    sys.exit()

from gpodder.liblogger import log
from email.Utils import mktime_tz
from email.Utils import parsedate_tz
from email.Utils import formatdate
from threading import RLock
import string

class Storage(object):
    (STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED) = range(3)

    lock = None

    def __init__(self):
        self.settings = {}
        self.channel_map = {}
        self._db = None
        self.lock = RLock()

    def setup(self, settings):
        self.settings = settings
        self.__check_schema()

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite.connect(self.settings['database'], check_same_thread=False)
            self._db.create_collation("unicode", lambda a, b: cmp(a.lower().replace('the ', ''), b.lower().replace('the ', '')))
            log('SQLite connected', sender=self)
        return self._db

    def cursor(self, lock=False):
        if lock:
            self.lock.acquire()
        return self.db.cursor()

    def commit(self):
        self.lock.acquire()
        try:
            self.db.commit()
        except ProgrammingError, e:
            log('Error commiting changes: %s', e, sender=self, traceback=True)
        self.lock.release()

    def __check_schema(self):
        """
        Creates all necessary tables and indexes that don't exist.
        """
        log('Setting up SQLite database', sender=self)

        cur = self.cursor(lock=True)

        cur.execute("""CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            override_title TEXT,
            link TEXT,
            description TEXT,
            image TEXT,
            pubDate INTEGER,
            sync_to_devices INTEGER,
            device_playlist_name TEXT,
            username TEXT,
            password TEXT,
            last_modified TEXT,
            etag TEXT,
            deleted INTEGER
            )""")
        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_url ON channels (url)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_sync_to_devices ON channels (sync_to_devices)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_title ON channels (title)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_deleted ON channels (deleted)""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                url TEXT,
                title TEXT,
                length INTEGER,
                mimetype TEXT,
                guid TEXT,
                description TEXT,
                link TEXT,
                pubDate INTEGER,
                state INTEGER,
                played INTEGER,
                locked INTEGER
                )
            """)
        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_guid ON episodes (guid)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_channel_id ON episodes (channel_id)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_pubDate ON episodes (pubDate)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_state ON episodes (state)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_played ON episodes (played)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_locked ON episodes (locked)""")

        cur.close()
        self.lock.release()

    def get_channel_stat(self, url_or_id, state=None, is_played=None, is_locked=None):
        where, params = ((),())

        if state is not None:
            where += ("state = ?", )
            params += (state, )
        if is_played is not None:
            where += ("played = ?", )
            params += (is_played, )
        if is_locked is not None:
            where += ("locked = ?", )
            params += (is_locked, )
        if isinstance(url_or_id, int):
            where += ("channel_id = ?", )
            params += (url_or_id, )
        else:
            where += ("channel_id IN (SELECT id FROM channels WHERE url = ?)", )
            params += (url_or_id, )

        if len(where):
            return self.__get__("SELECT COUNT(*) FROM episodes WHERE %s" % (' AND '.join(where)), params)
        else:
            return 0

    def load_channels(self, factory=None, url=None):
        """
        Returns channel descriptions as a list of dictionaries or objects,
        returned by the factory() function, which receives the dictionary
        as the only argument.
        """

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
                etag
            FROM
                channels
            WHERE
                (deleted IS NULL OR deleted = 0)
            ORDER BY
                title COLLATE unicode
                """)

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
                }

            if url is None:
                # Maintain url/id relation for faster updates (otherwise
                # we'd need to issue an extra query to find the channel id).
                self.channel_map[channel['url']] = channel['id']

            if url is None or url == channel['url']:
                if factory is None:
                    result.append(channel)
                else:
                    result.append(factory(channel))

        cur.close()
        self.lock.release()

        if url is None:
            log('Channel list read, %d entries.', len(result), sender=self)
        else:
            log('Channel %s read from db', url, sender=self)

        return result

    def save_channel(self, c, bulk=False):
        if c.id is None:
            c.id = self.find_channel_id(c.url)

        cur = self.cursor(lock=True)

        if c.id is None:
            cur.execute("INSERT INTO channels (url, title, override_title, link, description, image, pubDate, sync_to_devices, device_playlist_name, username, password, last_modified, etag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, ))
            self.channel_map[c.url] = cur.lastrowid
            log('Added channel %s[%d]', c.url, self.channel_map[c.url], sender=self)
        else:
            cur.execute("UPDATE channels SET url = ?, title = ?, override_title = ?, link = ?, description = ?, image = ?, pubDate = ?, sync_to_devices = ?, device_playlist_name = ?, username = ?, password = ?, last_modified = ?, etag = ?, deleted = 0 WHERE id = ?", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, c.id, ))

        if not bulk:
            self.commit()

        cur.close()
        self.lock.release()

    def delete_channel(self, channel, purge=False):
        if channel.id is None:
            channel.id = self.find_channel_id(channel.url)

        cur = self.cursor(lock=True)
        log('Deleting channel %d', channel.id, sender=self)

        if purge:
            cur.execute("DELETE FROM channels WHERE id = ?", (channel.id, ))
            cur.execute("DELETE FROM episodes WHERE channel_id = ?", (channel.id, ))
            if channel.url in self.channel_map:
                del self.channel_map[channel.url]
        else:
            cur.execute("UPDATE channels SET deleted = 1 WHERE id = ?", (channel.id, ))
            cur.execute("DELETE FROM episodes WHERE channel_id = ? AND state <> ?", (channel.id, self.STATE_DELETED))

        self.commit()
        cur.close()
        self.lock.release()

    def __read_episodes(self, factory=None, where=None, params=None, commit=True):
        sql = "SELECT url, title, length, mimetype, guid, description, link, pubDate, state, played, locked FROM episodes"

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
                }
            if episode['state'] is None:
                episode['state'] = self.STATE_NORMAL
            if factory is None:
                result.append(episode)
            else:
                result.append(factory(episode))

        cur.close()
        self.lock.release()
        return result

    def load_episodes(self, channel, factory=None, limit=1000, state=None):
        if channel.id is None:
            channel.id = self.find_channel_id(channel.url)

        if state is None:
            return self.__read_episodes(factory = factory, where = """
                WHERE channel_id = ? AND state = ? OR id IN
                (SELECT id FROM episodes WHERE channel_id = ?
                ORDER BY pubDate DESC LIMIT ?)
                ORDER BY pubDate DESC
                """, params = (channel.id, self.STATE_DOWNLOADED, channel.id, limit, ))
        else:
            return self.__read_episodes(factory = factory, where = " WHERE channel_id = ? AND state = ? ORDER BY pubDate DESC LIMIT ?", params = (channel.id, state, limit, ))

    def load_episode(self, url, factory=None):
        list = self.__read_episodes(factory = factory, where = " WHERE url = ?", params = (url, ))
        if len(list):
            return list[0]

    def save_episode(self, e, bulk=False):
        if not e.guid:
            log('Refusing to save an episode without guid: %s', e)
            return

        self.lock.acquire()

        try:
            cur = self.cursor()
            channel_id = self.find_channel_id(e.channel.url)

            if e.id is None:
                e.id = self.__get__("SELECT id FROM episodes WHERE guid = ?", (e.guid, ))

            if e.id is None:
                log('Episode added: %s', e.title)
                cur.execute("INSERT INTO episodes (channel_id, url, title, length, mimetype, guid, description, link, pubDate, state, played, locked) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (channel_id, e.url, e.title, e.length, e.mimetype, e.guid, e.description, e.link, self.__mktime__(e.pubDate), e.state, e.is_played, e.is_locked, ))
                e.id = cur.lastrowid
            else:
                log('Episode updated: %s', e.title)
                cur.execute("UPDATE episodes SET title = ?, length = ?, mimetype = ?, description = ?, link = ?, pubDate = ? WHERE id = ?", (e.title, e.length, e.mimetype, e.description, e.link, self.__mktime__(e.pubDate), e.id, ))
        except Exception, e:
            log('save_episode() failed: %s', e, sender=self)

        cur.close()
        self.commit()
        self.lock.release()

    def mark_episode(self, url, state=None, is_played=None, is_locked=None, toggle=False):
        cur = self.cursor(lock=True)
        cur.execute("SELECT state, played, locked FROM episodes WHERE url = ?", (url, ))

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

        self.commit()
        self.lock.release()

    def __get__(self, sql, params=None):
        """
        Returns the first cell of a query result, useful for COUNT()s.
        """
        cur = self.cursor(lock=True)

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

    def find_channel_id(self, url):
        """
        Looks up the channel id in the map (which lists all undeleted
        channels), then tries to look it up in the database, including
        deleted channels.
        """
        if url in self.channel_map.keys():
            return self.channel_map[url]
        else:
            return self.__get__("SELECT id FROM channels WHERE url = ?", (url, ))

    def force_last_new(self, channel):
        old = self.__get__("""SELECT COUNT(*) FROM episodes WHERE channel_id = ?
            AND state IN (?, ?)""", (channel.id, self.STATE_DOWNLOADED,
            self.STATE_DELETED))
        log('old episodes in (%d)%s: %d', channel.id, channel.url, old)

        cur = self.cursor(lock=True)

        if old > 0:
            cur.execute("""
                UPDATE episodes SET played = 1 WHERE channel_id = ?
                AND played = 0 AND pubDate < (SELECT MAX(pubDate)
                FROM episodes WHERE channel_id = ? AND state IN (?, ?))""",
                (channel.id, channel.id, self.STATE_DOWNLOADED,
                self.STATE_DELETED, ))
        else:
            cur.execute("""
                UPDATE episodes SET played = 1 WHERE channel_id = ?
                AND pubDate <> (SELECT MAX(pubDate) FROM episodes
                WHERE channel_id = ?)""", (channel.id, channel.id, ))

        self.commit()
        cur.close()
        self.lock.release()

db = Storage()
