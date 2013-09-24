#!/usr/bin/env python3
#
# convert_sqlite_to_jsondb: Convert gPodder 3 SQLite DB to gPodder 4 JSON DB
# Copyright (c) 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gpodder import model
from gpodder import storage

import sqlite3.dbapi2 as sqlite3


class Database(object):
    def __init__(self, filename):
        self.db = sqlite3.connect(filename)
        # Make sure you install the latest gPodder 3 version first before upgrading
        assert self.db.execute('SELECT version FROM version').fetchone()[0] == 5

    def load_podcasts(self):
        cur = self.db.cursor()
        cur.execute('SELECT * FROM podcast')
        keys = [desc[0] for desc in cur.description]
        for row in cur:
            yield dict(zip(keys, row))

    def load_episodes(self, podcast):
        cur = self.db.cursor()
        cur.execute('SELECT * FROM episode WHERE podcast_id = ?', (podcast.id,))
        keys = [desc[0] for desc in cur.description]
        for row in cur:
            yield dict(zip(keys, row))


if len(sys.argv) != 2:
    print("""
    Usage: {progname} /path/to/Database
    """.format(progname=sys.argv[0]), file=sys.stderr)
    sys.exit(1)

db_in = Database(sys.argv[1])
db_out = storage.Database(sys.argv[1])

for podcast_dict in db_in.load_podcasts():
    podcast = model.PodcastChannel(None)
    for key, value in podcast_dict.items():
        setattr(podcast, key, value)
    db_out.save_podcast(podcast)

    for episode_dict in db_in.load_episodes(podcast):
        episode = model.PodcastEpisode(podcast)
        for key, value in episode_dict.items():
            setattr(episode, key, value)
        db_out.save_episode(episode)

db_out.close()
