# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

# gpodder.pipe - Socket/pipe-based backend for New UIs
# Thomas Perl <thp@gpodder.org>; 2012-11-24


import gpodder

from gpodder import core
from gpodder import model
from gpodder import util
from gpodder import coverart

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

import os
import re
import sys
import threading
import Queue
import time
import fcntl

def cmd(*signature):
    def wrapper(f):
        setattr(f, '_pipecmd', True)
        return f
    return wrapper

def to_json(o):
    keys = list(('id',) + o.__slots__)
    values = list(getattr(o, key) for key in keys)
    yield keys
    yield values

class PipeError(BaseException): pass

class Pipe:
    def __init__(self, core, reader, writer):
        self.core = core

        self.model = self.core.model
        self.cover_download = coverart.CoverDownloader()

        self.reader = reader
        self.writer = writer
        self.events_in = Queue.Queue()
        self.events_out = Queue.Queue()

    def event_writer_proc(self):
        while True:
            item = self.events_out.get(True)
            self.writer.write(item.encode('utf-8') + '\n')
            self.writer.flush()

    def event_reader_proc(self):
        while True:
            args = self.events_in.get(True)
            cmd = args.pop(0)
            func = getattr(self, cmd, None)
            if func is not None:
                if getattr(func, '_pipecmd', False):
                    try:
                        result = func(*args)
                        if result:
                            self.event_out(result)
                    except PipeError, e:
                        self.event_out('! %s' % e)
                    except Exception, e:
                        print >>sys.stderr, 'FAIL:', e
                        self.event_out('! %s' % e)
                        raise
                    continue

            self.event_out('? %s' % cmd)

    def event_in(self, data):
        self.events_in.put(data)

    def event_out(self, data):
        self.events_out.put(data)

    def find_episode(self, id):
        for podcast in self.model.get_podcasts():
            for episode in podcast.get_all_episodes():
                if episode.id == int(id):
                    return episode
        raise PipeError('episode not found')

    def find_podcast(self, id):
        for podcast in self.model.get_podcasts():
            if podcast.id == int(id):
                return podcast
        raise PipeError('podcast not found')

    def summarize_podcasts(self, podcasts):
        yield ('id', 'title', 'downloads', 'cover')
        for podcast in podcasts:
            total, deleted, new, downloaded, unplayed = podcast.get_statistics()
            cover_filename = self.cover_download.get_cover(podcast.cover_file,
                    podcast.cover_url, podcast.url, podcast.title,
                    podcast.auth_username, podcast.auth_password, False)
            yield (podcast.id, podcast.title, downloaded, cover_filename)

    def summarize_episodes(self, episodes):
        yield ('id', 'title', 'state')
        for episode in episodes:
            yield (episode.id, episode.title, episode.state)

    def serialize(self, data):
        return json.dumps(list(data), ensure_ascii=False)

    @cmd()
    def podcasts(self):
        return 'podcasts ' + self.serialize(self.summarize_podcasts(self.model.get_podcasts()))

    @cmd(int)
    def episodes(self, id):
        podcast = self.find_podcast(id)
        return 'episodes ' + id + ' ' + self.serialize(self.summarize_episodes(podcast.get_all_episodes()))

    @cmd(int)
    def episode(self, id):
        episode = self.find_episode(id)
        return 'episode ' + id + ' ' + self.serialize(to_json(episode))

    @cmd(int)
    def podcast(self, id):
        podcast = self.find_podcast(id)
        return 'podcast ' + id + ' ' + self.serialize(to_json(podcast))

    @cmd()
    def update_all(self):
        @util.run_in_background
        def update_proc():
            for podcast in self.model.get_podcasts():
                self.event_out('updating %d' % podcast.id)
                podcast.update()
                self.event_out('updated %d' % podcast.id)
            self.event_out('updated_all')

    @cmd(int)
    def update(self, id):
        @util.run_in_background
        def update_proc():
            podcast = self.find_podcast(id)
            self.event_out('updating %d' % podcast.id)
            podcast.update()
            self.event_out('updated %d' % podcast.id)

    def run(self):
        def post_random_events():
            while True:
                time.sleep(1)
                self.event_out('hello')
                time.sleep(2)
                self.event_out('hello 10')
        random_event_thread = threading.Thread(target=post_random_events)
        random_event_thread.setDaemon(True)
        #random_event_thread.start()

        reader_thread = threading.Thread(target=self.event_reader_proc)
        writer_thread = threading.Thread(target=self.event_writer_proc)
        reader_thread.setDaemon(True)
        writer_thread.setDaemon(True)
        reader_thread.start()
        writer_thread.start()

        while True:
            line = self.reader.readline()
            if not line:
                break
            line = line.rstrip()
            if line:
                self.event_in(line.split())

def main(core):
    pipe = Pipe(core, sys.stdin, sys.stdout)
    pipe.run()

