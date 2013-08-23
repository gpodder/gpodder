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

from gpodder.compat import dbsqlite
from gpodder import storage

if len(sys.argv) != 2:
    print("""
    Usage: {progname} /path/to/Database
    """.format(progname=sys.argv[0]), file=sys.stderr)
    sys.exit(1)

db_in = dbsqlite.Database(sys.argv[1])
db_out = storage.Database(sys.argv[1])

for podcast_dict in db_in.load_podcasts(dict):
    podcast = model.PodcastChannel(None)
    for key, value in podcast_dict.items():
        setattr(podcast, key, value)
    db_out.save_podcast(podcast)

    for episode_dict in db_in.load_episodes(podcast, dict):
        episode = model.PodcastEpisode(podcast)
        for key, value in episode_dict.items():
            setattr(episode, key, value)
        db_out.save_episode(episode)

db_out.close()
db_in.close()

