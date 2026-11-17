# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

import os
import sqlite3

import gpodder
from gpodder import config, dbsqlite, model, util
from gpodder.download import DownloadTask


class NoExtensions:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class LocalDownloader:
    def __init__(self, url):
        self.url = url

    def custom_downloader(self, config, episode):
        return self

    def retrieve_resume(self, filename, reporthook):
        with open(filename, 'wb') as f:
            f.write(b'episode')
        return {'content-type': 'audio/mpeg'}, self.url


def make_directory(path):
    os.makedirs(path, exist_ok=True)
    return True


def test_finished_download_is_visible_to_other_connections(tmp_path, monkeypatch):
    # util.make_directory needs GIO, which the unit tests run without
    monkeypatch.setattr(util, 'make_directory', make_directory)
    monkeypatch.setattr(gpodder, 'downloads', str(tmp_path / 'Downloads'))
    monkeypatch.setattr(gpodder, 'user_extensions', NoExtensions())
    db_file = str(tmp_path / 'Database')
    db = dbsqlite.Database(db_file)

    podcasts = model.Model(db)
    podcasts.get_podcasts()

    podcast = model.PodcastChannel(podcasts)
    podcast.url = 'http://example.com/feed.xml'
    podcast.title = 'Podcast'
    podcast.save()
    episode = model.PodcastEpisode(podcast)
    episode.url = 'http://example.com/episode.mp3'
    episode.mime_type = 'audio/mpeg'
    episode.save()
    db.commit()

    settings = config.Config(str(tmp_path / 'Settings.json'))
    task = DownloadTask(episode, settings, downloader=LocalDownloader(episode.url))
    task.status = DownloadTask.DOWNLOADING
    assert task.run()

    other = sqlite3.connect(db_file)
    state, = other.execute('SELECT state FROM episode WHERE id = ?', (episode.id,)).fetchone()
    other.close()
    assert state == gpodder.STATE_DOWNLOADED
