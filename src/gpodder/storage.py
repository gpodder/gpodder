#
# gpodder.storage - JSON-based Database Backend (2013-05-20)
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


import json
import os
import gzip
import threading

from gpodder import util

class Database:
    def __init__(self, filename):
        self.filename = filename + '.jsondb'
        self.sequence_lock = threading.Lock()

        self._data = {
            'podcast': {},
            'episode': {},
            'sequence': {
                'podcast': 1,
                'episode': 1,
            },
        }

        if os.path.exists(self.filename):
            data = str(gzip.open(self.filename, 'rb').read(), 'utf-8')
            self._data = json.loads(data)

    def _read_object(self, id, table):
        yield ('id', int(id))
        for key, value in self._data[table][id].items():
            yield (key, value)

    def _update_object(self, o, table):
        def next_id():
            with self.sequence_lock:
                next_id = self._data['sequence'][table]
                self._data['sequence'][table] = next_id + 1
            return next_id

        if o.id is None:
            o.id = next_id()

        self._data[table][str(o.id)] = {k: getattr(o, k) for k in o.__schema__}

    def load_podcasts(self, podcast_factory):
        """Load all podcasts"""
        return [podcast_factory(self._read_object(k, 'podcast'))
                for k in self._data['podcast']]

    def load_episodes(self, podcast, episode_factory):
        """Load episodes for podcast"""
        return [episode_factory(self._read_object(k, 'episode'))
                for k in self._data['episode']
                if self._data['episode'][k]['podcast_id'] == podcast.id]

    def save_podcast(self, podcast):
        """Save a podcast (update or insert; on insert, set podcast.id)"""
        self._update_object(podcast, 'podcast')

    def save_episode(self, episode):
        """Save an episode (update or insert; on insert, set episode.id)"""
        self._update_object(episode, 'episode')

    def delete_podcast(self, podcast):
        """Delete podcast and all associated episodes"""
        del self._data['podcast'][str(podcast.id)]

    def delete_episode(self, episode):
        """Delete episode from database"""
        del self._data['episode'][str(episode.id)]

    def close(self):
        """Close and store outstanding changes"""
        with util.update_file_safely(self.filename) as filename:
            with gzip.open(filename, 'wb') as fp:
                data = bytes(json.dumps(self._data, separators=(',', ':')), 'utf-8')
                fp.write(data)

