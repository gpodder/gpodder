#!/usr/bin/env python3
# Convert gPodder 3 SQLite Database to gPodder 4 JSON Database
# Thomas Perl <m@thp.io>; 2013-05-20

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

