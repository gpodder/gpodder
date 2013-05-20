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


# JSON-based Database Backend for gPodder 4
# 2013-05-20 Thomas Perl <thp@gpodder.org>


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
            self._data = json.load(gzip.open(self.filename, 'rt'))

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
        """Load all podcasts (no particular order)"""
        return [podcast_factory(self._read_object(k, 'podcast'))
                for k in self._data['podcast']]

    def load_episodes(self, podcast, episode_factory):
        """Load episodes for podcast in decreasing "published" order"""
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
            with gzip.open(filename, 'wt') as fp:
                json.dump(self._data, fp, separators=(',', ':'))

