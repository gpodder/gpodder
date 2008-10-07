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

    def log(self, message, *args, **kwargs):
        if self.settings['gl'].config.log_sqlite:
            try:
                message = message % args
                log(message, sender=self)
            except TypeError, e:
                log('Exception in log(): %s: %s', e, message, sender=self)

    def purge(self, max_episodes, channel_id=None):
        """
        Deletes old episodes.  Should be called
        before adding new episodes to a channel.
        """
        cur = self.cursor(lock=True)

        if channel_id is None:
            cur.execute("SELECT channel_id, COUNT(*) AS count FROM episodes GROUP BY channel_id HAVING count > ?", (max_episodes, ))
        else:
            cur.execute("SELECT channel_id, COUNT(*) AS count FROM episodes WHERE channel_id = ? GROUP BY channel_id HAVING count > ?", (channel_id, max_episodes, ))

        self.log("purge(%s)", channel_id)

        for row in cur.fetchall():
            self.log("purge() -- deleting episodes in %d", row[0])
            sql = """
                DELETE FROM episodes
                WHERE channel_id = %d
                AND state <> %d
                AND id NOT IN
                (SELECT id FROM episodes WHERE channel_id = %d
                ORDER BY pubDate DESC LIMIT %d)""" % (row[0], self.STATE_DOWNLOADED, row[0], max_episodes)
            cur.execute(sql)

        cur.close()
        self.lock.release()

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite.connect(self.settings['database'], check_same_thread=False)
            self._db.create_collation("unicode", lambda a, b: cmp(a.lower().replace('the ', ''), b.lower().replace('the ', '')))
            self.log('Connected')
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

        cur.execute("""CREATE TEMPORARY VIEW episodes_downloaded AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE state = 1 GROUP BY channel_id""")
        cur.execute("""CREATE TEMPORARY VIEW episodes_new AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE state = 0 AND played = 0 GROUP BY channel_id""")
        cur.execute("""CREATE TEMPORARY VIEW episodes_unplayed AS SELECT channel_id, COUNT(*) AS count FROM episodes WHERE played = 0 AND state = %d GROUP BY channel_id""" % self.STATE_DOWNLOADED)

        # Make sure deleted episodes are played, to simplify querying statistics.
        cur.execute("UPDATE episodes SET played = 1 WHERE state = ?", (self.STATE_DELETED, ))

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

        self.log("get_channel_stats(%s)", url_or_id)

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
                etag
            FROM
                channels
            WHERE
                (deleted IS NULL OR deleted = 0)
            ORDER BY
                title COLLATE unicode
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
                    result.append(factory(channel))

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

    def save_channel(self, c, bulk=False):
        if c.id is None:
            c.id = self.find_channel_id(c.url)

        cur = self.cursor(lock=True)
        self.log("save_channel((%s)%s)", c.id or "new", c.url)

        if c.id is None:
            cur.execute("INSERT INTO channels (url, title, override_title, link, description, image, pubDate, sync_to_devices, device_playlist_name, username, password, last_modified, etag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, ))
            self.channel_map[c.url] = cur.lastrowid
        else:
            cur.execute("UPDATE channels SET url = ?, title = ?, override_title = ?, link = ?, description = ?, image = ?, pubDate = ?, sync_to_devices = ?, device_playlist_name = ?, username = ?, password = ?, last_modified = ?, etag = ?, deleted = 0 WHERE id = ?", (c.url, c.title, c.override_title, c.link, c.description, c.image, self.__mktime__(c.pubDate), c.sync_to_devices, c.device_playlist_name, c.username, c.password, c.last_modified, c.etag, c.id, ))

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
            cur.execute("DELETE FROM episodes WHERE channel_id = ? AND state <> ?", (channel.id, self.STATE_DELETED))

        cur.close()
        self.lock.release()

    def __read_episodes(self, factory=None, where=None, params=None, commit=True):
        sql = "SELECT url, title, length, mimetype, guid, description, link, pubDate, state, played, locked, id FROM episodes"

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
                'id': row[11],
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

        self.log("load_episodes((%d)%s)", channel.id, channel.url)

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
        self.log("load_episode(%s)", url)
        list = self.__read_episodes(factory = factory, where = " WHERE url = ?", params = (url, ))
        if len(list):
            return list[0]

    def save_episode(self, e, bulk=False):
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
                cur.execute("INSERT INTO episodes (channel_id, url, title, length, mimetype, guid, description, link, pubDate, state, played, locked) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (channel_id, e.url, e.title, e.length, e.mimetype, e.guid, e.description, e.link, self.__mktime__(e.pubDate), e.state, e.is_played, e.is_locked, ))
                e.id = cur.lastrowid
            else:
                cur.execute("UPDATE episodes SET title = ?, length = ?, mimetype = ?, description = ?, link = ?, pubDate = ?, state = ?, played = ?, locked = ? WHERE id = ?", (e.title, e.length, e.mimetype, e.description, e.link, self.__mktime__(e.pubDate), e.state, e.is_played, e.is_locked, e.id, ))
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
            AND state IN (?, ?)""", (channel.id, self.STATE_DOWNLOADED,
            self.STATE_DELETED))

        cur = self.cursor(lock=True)

        self.log("force_last_new((%d)%s)", channel.id, channel.url)

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

        cur.close()
        self.lock.release()

db = Storage()
