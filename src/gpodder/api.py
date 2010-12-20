# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

"""Public developer API for gPodder

This module provides a nicely documented API for developers to
integrate podcast functionality into their applications.
"""

import gpodder
from gpodder import util
from gpodder import opml
from gpodder.model import PodcastChannel
from gpodder import download
from gpodder import console

from gpodder import dbsqlite
from gpodder import config
from gpodder import youtube

class Podcast(object):
    """API interface of gPodder podcasts

    This is the API specification of podcast objects that
    are returned from API functions.

    Public attributes:
      title
      url
    """
    def __init__(self, _podcast, _manager):
        """For internal use only."""
        self._podcast = _podcast
        self._manager = _manager
        self.title = self._podcast.title
        self.url = self._podcast.url

    def get_episodes(self):
        """Get all episodes that belong to this podcast

        Returns a list of Episode objects that belong to this podcast."""
        return [Episode(e, self._manager) for e in self._podcast.get_all_episodes()]

    def rename(self, title):
        """Set a new title for this podcast

        Sets a new title for this podcast that will be available
        as the "title" attribute of this object."""
        self._podcast.set_custom_title(title)
        self.title = self._podcast.title
        self._podcast.save()

    def delete(self):
        """Remove this podcast from the subscription list

        Removes the subscription and all downloaded episodes.
        """
        self._podcast.remove_downloaded()
        self._podcast.delete()
        self._podcast = None

    def update_enabled(self):
        """Check if this feed has updates enabled

        This function will return True if the podcast has feed
        updates enabled. If the user pauses a subscription, the
        feed updates are disabled, and the podcast should be
        excluded from automatic updates.
        """
        return self._podcast.feed_update_enabled

    def update(self):
        """Updates this podcast by downloading the feed

        Downloads the podcast feed (using the feed cache), and
        adds new episodes and updated information to the database.
        """
        self._podcast.update(self._manager._config.max_episodes_per_feed, \
                self._manager._config.mimetype_prefs)

    def feed_update_status_msg(self):
        """Show the feed update status
 
        Display the feed update current status.
        """
        if self._podcast.feed_update_enabled:
            return "enabled"
        else:
            return "disabled"

    def feed_update_status(self):
        """Return the feed update status

        Return the feed update current status.
        """
        return self._podcast.feed_update_enabled

    def disable(self):
        """Toogle the feed update to disable

        Change the feed update status to disable only if currently enable.
        """
        if self._podcast.feed_update_enabled:
            self._podcast.feed_update_enabled = False
            self._podcast.save()

    def enable(self):
        """Toogle the feed update to disable

        Change the feed update status to disable only if currently enable.
        """
        if not self._podcast.feed_update_enabled:
            self._podcast.feed_update_enabled = True
            self._podcast.save()

class Episode(object):
    """API interface of gPodder episodes

    This is the API specification of episode objects that
    are returned from API functions.

    Public attributes:
      title
      url
      is_new
      is_downloaded
      is_deleted
    """
    def __init__(self, _episode, _manager):
        """For internal use only."""
        self._episode = _episode
        self._manager = _manager
        self.title = self._episode.title
        self.url = self._episode.url
        self.is_new = (self._episode.state == gpodder.STATE_NORMAL and \
                not self._episode.is_played)
        self.is_downloaded = (self._episode.state == gpodder.STATE_DOWNLOADED)
        self.is_deleted = (self._episode.state == gpodder.STATE_DELETED)

    def download(self, callback=None):
        """Downloads the episode to a local file

        This will run the download in the same thread, so be sure
        to call this method from a worker thread in case you have
        a GUI running as a frontend."""
        task = download.DownloadTask(self._episode, self._manager._config)
        if callback is not None:
            task.add_progress_callback(callback)
        task.status = download.DownloadTask.QUEUED
        task.run()


class PodcastClient(object):
    def __init__(self):
        """Create a new gPodder API instance

        Connects to the database and loads the configuration.
        """
        util.make_directory(gpodder.home)
        gpodder.load_plugins()

        self._db = dbsqlite.Database(gpodder.database_file)
        self._config = config.Config(gpodder.config_file)

    def get_podcasts(self):
        """Get a list of Podcast objects

        Returns all the subscribed podcasts from gPodder.
        """
        return [Podcast(p, self) for p in PodcastChannel.load_from_db(self._db)]

    def get_podcast(self, url):
        """Get a specific podcast by URL

        Returns a podcast object for the URL or None if
        the podcast has not been subscribed to.
        """
        url = util.normalize_feed_url(url)
        channel = PodcastChannel.load(self._db, url, create=False)
        if channel is None:
            return None
        else:
            return Podcast(channel, self)

    def create_podcast(self, url, title=None):
        """Subscribe to a new podcast

        Add a subscription for "url", optionally
        renaming the podcast to "title" and return
        the resulting object.
        """
        url = util.normalize_feed_url(url)
        podcast = PodcastChannel.load(self._db, url, create=True, \
                max_episodes=self._config.max_episodes_per_feed, \
                mimetype_prefs=self._config.mimetype_prefs)
        if podcast is not None:
            if title is not None:
                podcast.set_custom_title(title)
            podcast.save()
            return Podcast(podcast, self)

        return None

    def synchronize_device(self):
        """Synchronize episodes to a device

        WARNING: API subject to change.
        """
        console.synchronize_device(self._db, self._config)

    def finish(self):
        """Persist changed data to the database file

        This has to be called from the API user after
        data-changing actions have been carried out.
        """
        podcasts = PodcastChannel.load_from_db(self._db)
        self._db.commit()
        return True

    def youtube_url_resolver(self, url): 
        """Resolve the Youtube URL

        WARNING: API subject to change.
        """
        yurl = youtube.get_real_download_url(url, \
            self._config.youtube_preferred_fmt_id)

        return yurl
