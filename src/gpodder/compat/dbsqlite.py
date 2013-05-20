# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

from sqlite3 import dbapi2 as sqlite

import logging
logger = logging.getLogger(__name__)

from gpodder.compat import schema
from gpodder import util

import threading
import re

class Database(object):
    TABLE_PODCAST = 'podcast'
    TABLE_EPISODE = 'episode'

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

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite.connect(self.database_file, check_same_thread=False)

            # Check schema version, upgrade if necessary
            schema.upgrade(self._db, self.database_file)

            logger.debug('Database opened.')
        return self._db

    def cursor(self):
        return self.db.cursor()

    def commit(self):
        with self.lock:
            try:
                logger.debug('Commit.')
                self.db.commit()
            except Exception as e:
                logger.error('Cannot commit: %s', e, exc_info=True)

    def load_podcasts(self, factory):
        logger.info('Loading podcasts')

        sql = 'SELECT * FROM %s' % self.TABLE_PODCAST

        with self.lock:
            cur = self.cursor()
            cur.execute(sql)

            keys = [desc[0] for desc in cur.description]
            result = [factory(zip(keys, row)) for row in cur]
            cur.close()

        return result

    def load_episodes(self, podcast, factory):
        assert podcast.id

        logger.info('Loading episodes for podcast %d', podcast.id)

        sql = 'SELECT * FROM %s WHERE podcast_id = ? ORDER BY published DESC' % self.TABLE_EPISODE
        args = (podcast.id,)

        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)

            keys = [desc[0] for desc in cur.description]
            result = [factory(zip(keys, row)) for row in cur]
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
            self.db.commit()

    def delete_episode(self, episode):
        assert episode.id

        with self.lock:
            cur = self.cursor()
            cur.execute('DELETE FROM %s WHERE id = ?' % self.TABLE_EPISODE, (episode.id,))
            cur.close()

    def save_podcast(self, podcast):
        self._save_object(podcast, self.TABLE_PODCAST, podcast.__schema__)

    def save_episode(self, episode):
        self._save_object(episode, self.TABLE_EPISODE, episode.__schema__)

    def _save_object(self, o, table, columns):
        with self.lock:
            try:
                cur = self.cursor()
                values = [util.convert_bytes(getattr(o, name))
                        for name in columns]

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
            except Exception as e:
                logger.error('Cannot save %s: %s', o, e, exc_info=True)

            cur.close()

