# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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


from PySide.QtCore import QObject, Property, Signal

import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import model
from gpodder import util
from gpodder import youtube
from gpodder import download
from gpodder import query
from gpodder import model

import threading
import os

def convert(s):
    if s is None:
        return None

    if isinstance(s, unicode):
        return s

    return s.decode('utf-8', 'ignore')

class QEpisode(QObject):
    def __init__(self, wrapper_manager, podcast, episode):
        QObject.__init__(self)
        self._wrapper_manager = wrapper_manager
        self.episode_wrapper_refcount = 0
        self._podcast = podcast
        self._episode = episode

        # Caching of YouTube URLs, so we don't need to resolve
        # it every time we update the podcast item (doh!)
        # XXX: Maybe do this in the episode of the model already?
        self._qt_yt_url = None

        # Download progress tracking XXX: read directy from task
        self._qt_download_progress = 0

        # Playback tracking
        self._qt_playing = False

    def __getattr__(self, name):
        logger.warn('Attribute access in %s: %s', self.__class__.__name__, name)
        return getattr(self._episode, name)

    def toggle_new(self):
        self._episode.mark(is_played=self._episode.is_new)
        self.changed.emit()
        self._podcast.changed.emit()

    def toggle_archive(self):
        self._episode.mark(is_locked=not self._episode.archive)
        self.changed.emit()
        self._podcast.changed.emit()

    def delete_episode(self):
        self._episode.delete_from_disk()
        self._episode.mark(is_played=True)
        self.changed.emit()
        self._podcast.changed.emit()
        self.source_url_changed.emit()

    changed = Signal()
    never_changed = Signal()
    source_url_changed = Signal()

    def _podcast(self):
        return self._podcast

    qpodcast = Property(QObject, _podcast, notify=never_changed)

    def _title(self):
        return convert(self._episode.trimmed_title)

    qtitle = Property(unicode, _title, notify=changed)

    def _sourceurl(self):
        if self._episode.was_downloaded(and_exists=True):
            url = self._episode.local_filename(create=False)
        elif self._qt_yt_url is not None:
            url = self._qt_yt_url
        else:
            url = youtube.get_real_download_url(self._episode.url)
            self._qt_yt_url = url
        return convert(url)

    qsourceurl = Property(unicode, _sourceurl, notify=source_url_changed)

    def _filetype(self):
        return self._episode.file_type() or 'download'

    qfiletype = Property(unicode, _filetype, notify=never_changed)

    def _downloaded(self):
        return self._episode.was_downloaded(and_exists=True)

    qdownloaded = Property(bool, _downloaded, notify=changed)

    def _downloading(self):
        return self._episode.downloading

    qdownloading = Property(bool, _downloading, notify=changed)

    def _playing(self):
        return self._qt_playing

    def _set_playing(self, playing):
        if self._qt_playing != playing:
            if playing:
                self._episode.playback_mark()
            self._qt_playing = playing
            self.changed.emit()

    qplaying = Property(bool, _playing, _set_playing, notify=changed)

    def _progress(self):
        return self._qt_download_progress

    qprogress = Property(float, _progress, notify=changed)

    def qdownload(self, config, finished_callback=None):
        # Avoid starting the same download twice
        if self.download_task is not None:
            return

        # Initialize the download task here, so that the
        # UI will be updated as soon as possible
        self._wrapper_manager.add_active_episode(self)
        self._qt_download_progress = 0.
        task = download.DownloadTask(self._episode, config)
        task.status = download.DownloadTask.QUEUED
        self.changed.emit()

        def t(self):
            def cb(progress):
                if progress > self._qt_download_progress + .01 or progress == 1:
                    self._qt_download_progress = progress
                    self.changed.emit()
            task.add_progress_callback(cb)
            task.run()
            task.recycle()
            task.removed_from_list()
            self.changed.emit()
            self.source_url_changed.emit()

            # Make sure the single channel is updated (main view)
            self._podcast.changed.emit()

            # Make sure that "All episodes", etc.. are updated
            if finished_callback is not None:
                finished_callback()

            self._wrapper_manager.remove_active_episode(self)

        thread = threading.Thread(target=t, args=[self])
        thread.setDaemon(True)
        thread.start()

    def _description(self):
        return convert(self._episode.description_html)

    qdescription = Property(unicode, _description, notify=changed)

    def _new(self):
        return self._episode.is_new

    qnew = Property(bool, _new, notify=changed)

    def _archive(self):
        return self._episode.archive

    qarchive = Property(bool, _archive, notify=changed)

    def _position(self):
        return self._episode.current_position

    def _set_position(self, position):
        current_position = int(position)
        if current_position == 0: return
        if current_position != self._episode.current_position:
            self._episode.current_position = current_position
            self.changed.emit()

    qposition = Property(int, _position, _set_position, notify=changed)

    def _duration(self):
        return self._episode.total_time

    def _set_duration(self, duration):
        total_time = int(duration)
        if total_time != self._episode.total_time:
            self._episode.total_time = total_time
            self.changed.emit()

    qduration = Property(int, _duration, _set_duration, notify=changed)


class QPodcast(QObject):
    def __init__(self, podcast):
        QObject.__init__(self)
        self._podcast = podcast
        self._updating = False

    @classmethod
    def sort_key(cls, qpodcast):
        if isinstance(qpodcast, cls):
            sortkey = model.Model.podcast_sort_key(qpodcast._podcast)
        else:
            sortkey = None

        return (qpodcast.qsection, sortkey)

    def __getattr__(self, name):
        logger.warn('Attribute access in %s: %s', self.__class__.__name__, name)
        return getattr(self._podcast, name)

    def qupdate(self, force=False, finished_callback=None):
        def t(self):
            self._updating = True
            self.changed.emit()
            if force:
                self._podcast.http_etag = None
                self._podcast.http_last_modified = None
            try:
                self._podcast.update()
            except Exception, e:
                # XXX: Handle exception (error message)!
                pass
            self._updating = False
            self.changed.emit()

            # Notify the caller that we've finished updating
            if finished_callback is not None:
                finished_callback()

        threading.Thread(target=t, args=[self]).start()

    changed = Signal()

    def _updating(self):
        return self._updating

    qupdating = Property(bool, _updating, notify=changed)

    def _title(self):
        return convert(self._podcast.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _url(self):
        return convert(self._podcast.url)

    qurl = Property(unicode, _url, notify=changed)

    def _coverfile(self):
        return convert(self._podcast.cover_file)

    qcoverfile = Property(unicode, _coverfile, notify=changed)

    def _coverurl(self):
        return convert(self._podcast.cover_url)

    qcoverurl = Property(unicode, _coverurl, notify=changed)

    def _downloaded(self):
        return self._podcast.get_statistics()[3]

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _new(self):
        return self._podcast.get_statistics()[2]

    qnew = Property(int, _new, notify=changed)

    def _description(self):
        return convert(util.get_first_line(self._podcast.description))

    qdescription = Property(unicode, _description, notify=changed)

    def _section(self):
        return convert(self._podcast.group_by)

    qsection = Property(unicode, _section, notify=changed)

    def set_section(self, section):
        self._podcast.section = section
        self._podcast.save()
        self.changed.emit()


class EpisodeSubsetView(QObject):
    def __init__(self, db, podcast_list_model, title, description, eql=None):
        QObject.__init__(self)
        self.db = db
        self.podcast_list_model = podcast_list_model
        self.title = title
        self.description = description
        self.eql = eql

        self._new_count = -1
        self._downloaded_count = -1

    def _update_stats(self):
        if self.eql is None:
            total, deleted, new, downloaded, unplayed = \
                    self.db.get_podcast_statistics()
        else:
            new, downloaded = 0, 0
            for episode in self.get_all_episodes():
                if episode.was_downloaded(and_exists=True):
                    downloaded += 1
                elif episode.is_new:
                    new += 1

        self._new_count = new
        self._downloaded_count = downloaded

    def _do_filter(self, items, is_tuple=False):
        """Filter a list of items via the attached SQL

        If is_tuple is True, the list of items should be a
        list of (podcast, episode) tuples, otherwise it
        should just be a list of episode objects.
        """
        if self.eql is not None:
            eql = query.EQL(self.eql)
            if is_tuple:
                match = lambda (podcast, episode): eql.match(episode)
            else:
                match = eql.match

            items = filter(match, items)

        return items

    def get_all_episodes_with_podcast(self):
        episodes = [(podcast, episode) for podcast in
                self.podcast_list_model.get_podcasts()
                for episode in podcast.get_all_episodes()]

        def sort_key(pair):
            podcast, episode = pair
            return model.Model.episode_sort_key(episode)

        return sorted(self._do_filter(episodes, is_tuple=True),
                key=sort_key, reverse=True)

    def get_all_episodes(self):
        episodes = []
        for podcast in self.podcast_list_model.get_podcasts():
            episodes.extend(podcast.get_all_episodes())

        return model.Model.sort_episodes_by_pubdate(
                self._do_filter(episodes), True)

    def qupdate(self, force=False, finished_callback=None):
        self._update_stats()
        self.changed.emit()

    changed = Signal()

    def _return_false(self):
        return False

    def _return_empty(self):
        return convert('')

    qupdating = Property(bool, _return_false, notify=changed)
    qurl = Property(unicode, _return_empty, notify=changed)
    qcoverfile = Property(unicode, _return_empty, notify=changed)
    qcoverurl = Property(unicode, _return_empty, notify=changed)
    qsection = Property(unicode, _return_empty, notify=changed)

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _description(self):
        return convert(self.description)

    qdescription = Property(unicode, _description, notify=changed)

    def _downloaded(self):
        if self._downloaded_count == -1:
            self._update_stats()
        return self._downloaded_count

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _new(self):
        if self._new_count == -1:
            self._update_stats()
        return self._new_count

    qnew = Property(int, _new, notify=changed)


