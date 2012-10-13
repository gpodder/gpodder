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

"""

                XXX DO NOT USE IN NEW CODE XXX

This "public API" was created at a time where the internal structure
of gPodder was very much in flux. Now, the situation has changed, and
this module should not be used anymore. It only exists, because the
"gpo" command-line utility still makes use of it.

In the not too distant future, this module will be removed and code
that is still useful will be moved into other modules (e.g. model or
core) or into the "gpo" command-line utility itself.

                XXX DO NOT USE IN NEW CODE XXX

"""

import gpodder

from gpodder import util
from gpodder import core
from gpodder import download

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
        self._podcast.rename(title)
        self.title = self._podcast.title
        self._podcast.save()

    def rewrite_url(self, url):
        """Set a new URL for this podcast

        Sets a new feed URL for this podcast. Use with care.
        See also: gPodder bug 1020
        """
        url = util.normalize_feed_url(url)
        if url is None:
            return None

        self._podcast.url = url

        # Remove etag + last_modified to force a refresh next time
        self._podcast.http_etag = None
        self._podcast.http_last_modified = None

        self._podcast.save()

        return url

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
        return not self._podcast.pause_subscription

    def update(self):
        """Updates this podcast by downloading the feed

        Downloads the podcast feed (using the feed cache), and
        adds new episodes and updated information to the database.
        """
        self._podcast.update(self._manager._config.max_episodes_per_feed)

    def feed_update_status_msg(self):
        """Show the feed update status
 
        Display the feed update current status.
        """
        if self._podcast.pause_subscription:
            return "disabled"
        else:
            return "enabled"

    def feed_update_status(self):
        """Return the feed update status

        Return the feed update current status.
        """
        return not self._podcast.pause_subscription

    def disable(self):
        """Toogle the feed update to disable

        Change the feed update status to disable only if currently enable.
        """
        if not self._podcast.pause_subscription:
            self._podcast.pause_subscription = True
            self._podcast.save()

    def enable(self):
        """Toogle the feed update to disable

        Change the feed update status to disable only if currently enable.
        """
        if self._podcast.pause_subscription:
            self._podcast.pause_subscription = False
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
                self._episode.is_new)
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
        self.core = core.Core()
        self._db = self.core.db
        self._model = self.core.model
        self._config = self.core.config

    def get_podcasts(self):
        """Get a list of Podcast objects

        Returns all the subscribed podcasts from gPodder.
        """
        return [Podcast(p, self) for p in self._model.get_podcasts()]

    def get_podcast(self, url):
        """Get a specific podcast by URL

        Returns a podcast object for the URL or None if
        the podcast has not been subscribed to.
        """
        url = util.normalize_feed_url(url)
        if url is None:
            return None
        channel = self._model.load_podcast(url, create=False)
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
        if url is None:
            return None

        podcast = self._model.load_podcast(url, create=True, \
                max_episodes=self._config.max_episodes_per_feed)
        if podcast is not None:
            if title is not None:
                podcast.rename(title)
            podcast.save()
            return Podcast(podcast, self)

        return None

    def commit(self):
        """Persist changed data to the database file

        Call this after a user operation has been
        carried out, but if you don't want to close the
        application (otherwise simply use finish()).
        """
        self._db.commit()

    def finish(self):
        """Persist changed data to the database file

        This has to be called from the API user after
        data-changing actions have been carried out.
        """
        self.core.shutdown()
        return True

    def youtube_url_resolver(self, url): 
        """Resolve the Youtube URL

        WARNING: API subject to change.
        """

        fmt_ids = youtube.formats.get(self._config.youtube_preferred_fmt_id, ([]))[0] \
            if not self._config.youtube_preferred_fmt_ids \
            else self._config.youtube_preferred_fmt_ids

        yurl = youtube.get_real_download_url(url, fmt_ids)

        return yurl
