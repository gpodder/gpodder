# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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


#
#  gpodder.model - Core model classes for gPodder (2009-08-13)
#  Based on libpodcasts.py (thp, 2005-10-29)
#

import gpodder
from gpodder import util
from gpodder import feedcore
from gpodder import youtube
from gpodder import corestats

from gpodder.liblogger import log

import os
import re
import glob
import shutil
import urllib
import urlparse
import time
import datetime
import rfc822
import hashlib
import feedparser
import xml.sax.saxutils

_ = gpodder.gettext


class gPodderFetcher(feedcore.Fetcher):
    """
    This class extends the feedcore Fetcher with the gPodder User-Agent and the
    Proxy handler based on the current settings in gPodder and provides a
    convenience method (fetch_channel) for use by PodcastChannel objects.
    """

    def __init__(self):
        feedcore.Fetcher.__init__(self, gpodder.user_agent)

    def fetch_channel(self, channel):
        etag = channel.etag
        modified = feedparser._parse_date(channel.last_modified)
        # If we have a username or password, rebuild the url with them included
        # Note: using a HTTPBasicAuthHandler would be pain because we need to
        # know the realm. It can be done, but I think this method works, too
        url = channel.authenticate_url(channel.url)
        self.fetch(url, etag, modified)

    def _resolve_url(self, url):
        return youtube.get_real_channel_url(url)

#    def _get_handlers(self):
#        # Add a ProxyHandler for fetching data via a proxy server
#        proxies = {'http': 'http://proxy.example.org:8080'}
#        return[urllib2.ProxyHandler(proxies))]


class PodcastModelObject(object):
    """
    A generic base class for our podcast model providing common helper
    and utility functions.
    """

    @classmethod
    def create_from_dict(cls, d, *args):
        """
        Create a new object, passing "args" to the constructor
        and then updating the object with the values from "d".
        """
        o = cls(*args)
        o.update_from_dict(d)
        return o

    def update_from_dict(self, d):
        """
        Updates the attributes of this object with values from the
        dictionary "d" by using the keys found in "d".
        """
        for k in d:
            if hasattr(self, k):
                setattr(self, k, d[k])


class PodcastChannel(PodcastModelObject):
    """holds data for a complete channel"""
    MAX_FOLDERNAME_LENGTH = 150

    feed_fetcher = gPodderFetcher()

    @classmethod
    def build_factory(cls, download_dir):
        def factory(dict, db):
            return cls.create_from_dict(dict, db, download_dir)
        return factory

    @classmethod
    def load_from_db(cls, db, download_dir):
        return db.load_channels(factory=cls.build_factory(download_dir))

    @classmethod
    def load(cls, db, url, create=True, authentication_tokens=None,\
            max_episodes=0, download_dir=None):
        if isinstance(url, unicode):
            url = url.encode('utf-8')

        tmp = db.load_channels(factory=cls.build_factory(download_dir), url=url)
        if len(tmp):
            return tmp[0]
        elif create:
            tmp = PodcastChannel(db, download_dir)
            tmp.url = url
            if authentication_tokens is not None:
                tmp.username = authentication_tokens[0]
                tmp.password = authentication_tokens[1]

            tmp.update(max_episodes)
            tmp.save()
            db.force_last_new(tmp)
            # Subscribing to empty feeds should yield an error
            if sum(tmp.get_statistics()) == 0:
                tmp.delete()
                raise Exception(_('No downloadable episodes in feed'))
            return tmp

    def episode_factory(self, d, db__parameter_is_unused=None):
        """
        This function takes a dictionary containing key-value pairs for
        episodes and returns a new PodcastEpisode object that is connected
        to this PodcastChannel object.

        Returns: A new PodcastEpisode object
        """
        return PodcastEpisode.create_from_dict(d, self)

    def _consume_updated_feed(self, feed, max_episodes=0):
        self.parse_error = feed.get('bozo_exception', None)

        self.title = feed.feed.get('title', self.url)
        self.link = feed.feed.get('link', self.link)
        self.description = feed.feed.get('subtitle', self.description)
        # Start YouTube-specific title FIX
        YOUTUBE_PREFIX = 'Uploads by '
        if self.title.startswith(YOUTUBE_PREFIX):
            self.title = self.title[len(YOUTUBE_PREFIX):] + ' on YouTube'
        # End YouTube-specific title FIX

        try:
            self.pubDate = rfc822.mktime_tz(feed.feed.get('updated_parsed', None+(0,)))
        except:
            self.pubDate = time.time()

        if hasattr(feed.feed, 'image'):
            if hasattr(feed.feed.image, 'href') and feed.feed.image.href:
                old = self.image
                self.image = feed.feed.image.href

        self.save()

        # Load all episodes to update them properly.
        existing = self.get_all_episodes()

        # We can limit the maximum number of entries that gPodder will parse
        if max_episodes > 0 and len(feed.entries) > max_episodes:
            entries = feed.entries[:max_episodes]
        else:
            entries = feed.entries

        # Search all entries for new episodes
        for entry in entries:
            episode = None

            try:
                episode = PodcastEpisode.from_feedparser_entry(entry, self)
            except Exception, e:
                log('Cannot instantiate episode "%s": %s. Skipping.', entry.get('id', '(no id available)'), e, sender=self, traceback=True)

            if episode:
                self.count_new += 1

                for ex in existing:
                    if ex.guid == episode.guid or episode.is_duplicate(ex):
                        for k in ('title', 'url', 'description', 'link', 'pubDate', 'guid'):
                            setattr(ex, k, getattr(episode, k))
                        self.count_new -= 1
                        episode = ex

                episode.save()

        # Remove "unreachable" episodes - episodes that have not been
        # downloaded and that the feed does not list as downloadable anymore
        if self.id is not None:
            seen_guids = set(e.guid for e in feed.entries if hasattr(e, 'guid'))
            episodes_to_purge = (e for e in existing if \
                    e.state != gpodder.STATE_DOWNLOADED and \
                    e.guid not in seen_guids and e.guid is not None)
            for episode in episodes_to_purge:
                log('Episode removed from feed: %s (%s)', episode.title, \
                        episode.guid, sender=self)
                self.db.delete_episode_by_guid(episode.guid, self.id)

        # This *might* cause episodes to be skipped if there were more than
        # max_episodes_per_feed items added to the feed between updates.
        # The benefit is that it prevents old episodes from apearing as new
        # in certain situations (see bug #340).
        self.db.purge(max_episodes, self.id)

    def update_channel_lock(self):
        self.db.update_channel_lock(self)

    def _update_etag_modified(self, feed):
        self.updated_timestamp = time.time()
        self.calculate_publish_behaviour()
        self.etag = feed.headers.get('etag', self.etag)
        self.last_modified = feed.headers.get('last-modified', self.last_modified)

    def query_automatic_update(self):
        """Query if this channel should be updated automatically

        Returns True if the update should happen in automatic
        mode or False if this channel should be skipped (timeout
        not yet reached or release not expected right now).
        """
        updated = self.updated_timestamp
        expected = self.release_expected

        now = time.time()
        one_day_ago = now - 60*60*24
        lastcheck = now - 60*10

        return updated < one_day_ago or \
                (expected < now and updated < lastcheck)

    def update(self, max_episodes=0):
        try:
            self.feed_fetcher.fetch_channel(self)
        except feedcore.UpdatedFeed, updated:
            feed = updated.data
            self._consume_updated_feed(feed, max_episodes)
            self._update_etag_modified(feed)
            self.save()
        except feedcore.NewLocation, updated:
            feed = updated.data
            self.url = feed.href
            self._consume_updated_feed(feed, max_episodes)
            self._update_etag_modified(feed)
            self.save()
        except feedcore.NotModified, updated:
            feed = updated.data
            self._update_etag_modified(feed)
            self.save()
        except Exception, e:
            # "Not really" errors
            #feedcore.AuthenticationRequired
            # Temporary errors
            #feedcore.Offline
            #feedcore.BadRequest
            #feedcore.InternalServerError
            #feedcore.WifiLogin
            # Permanent errors
            #feedcore.Unsubscribe
            #feedcore.NotFound
            #feedcore.InvalidFeed
            #feedcore.UnknownStatusCode
            raise

        self.db.commit()

    def delete(self, purge=True):
        self.db.delete_channel(self, purge)

    def save(self):
        self.db.save_channel(self)

    def get_statistics(self):
        if self.id is None:
            return (0, 0, 0, 0, 0)
        else:
            return self.db.get_channel_count(int(self.id))

    def authenticate_url(self, url):
        return util.url_add_authentication(url, self.username, self.password)

    def __init__(self, db, download_dir):
        self.db = db
        self.download_dir = download_dir
        self.id = None
        self.url = None
        self.title = ''
        self.link = ''
        self.description = ''
        self.image = None
        self.pubDate = 0
        self.parse_error = None
        self.newest_pubdate_cached = None
        self.foldername = None
        self.auto_foldername = 1 # automatically generated foldername

        # should this channel be synced to devices? (ex: iPod)
        self.sync_to_devices = True
        # to which playlist should be synced
        self.device_playlist_name = 'gPodder'
        # if set, this overrides the channel-provided title
        self.override_title = ''
        self.username = ''
        self.password = ''

        self.last_modified = None
        self.etag = None

        self.save_dir_size = 0
        self.__save_dir_size_set = False

        self.count_downloaded = 0
        self.count_new = 0
        self.count_unplayed = 0

        self.channel_is_locked = False

        self.release_expected = time.time()
        self.release_deviation = 0
        self.updated_timestamp = 0

    def calculate_publish_behaviour(self):
        episodes = self.db.load_episodes(self, factory=self.episode_factory, limit=30)
        if len(episodes) < 3:
            return

        deltas = []
        latest = max(e.pubDate for e in episodes)
        for index in range(len(episodes)-1):
            if episodes[index].pubDate != 0 and episodes[index+1].pubDate != 0:
                deltas.append(episodes[index].pubDate - episodes[index+1].pubDate)

        if len(deltas) > 1:
            stats = corestats.Stats(deltas)
            self.release_expected = min([latest+stats.stdev(), latest+(stats.min()+stats.avg())*.5])
            self.release_deviation = stats.stdev()
        else:
            self.release_expected = latest
            self.release_deviation = 0

    def request_save_dir_size(self):
        if not self.__save_dir_size_set:
            self.update_save_dir_size()
        self.__save_dir_size_set = True

    def update_save_dir_size(self):
        self.save_dir_size = util.calculate_size(self.save_dir)

    def get_title( self):
        if self.override_title:
            return self.override_title
        elif not self.__title.strip():
            return self.url
        else:
            return self.__title

    def set_title( self, value):
        self.__title = value.strip()

    title = property(fget=get_title,
                     fset=set_title)

    def set_custom_title( self, custom_title):
        custom_title = custom_title.strip()
        
        # if the custom title is the same as we have
        if custom_title == self.override_title:
            return
        
        # if custom title is the same as channel title and we didn't have a custom title
        if custom_title == self.__title and self.override_title == '':
            return

        # make sure self.foldername is initialized
        self.get_save_dir()

        # rename folder if custom_title looks sane
        new_folder_name = self.find_unique_folder_name(custom_title)
        if len(new_folder_name) > 0 and new_folder_name != self.foldername:
            log('Changing foldername based on custom title: %s', custom_title, sender=self)
            new_folder = os.path.join(self.download_dir, new_folder_name)
            old_folder = os.path.join(self.download_dir, self.foldername)
            if os.path.exists(old_folder):
                if not os.path.exists(new_folder):
                    # Old folder exists, new folder does not -> simply rename
                    log('Renaming %s => %s', old_folder, new_folder, sender=self)
                    os.rename(old_folder, new_folder)
                else:
                    # Both folders exist -> move files and delete old folder
                    log('Moving files from %s to %s', old_folder, new_folder, sender=self)
                    for file in glob.glob(os.path.join(old_folder, '*')):
                        shutil.move(file, new_folder)
                    log('Removing %s', old_folder, sender=self)
                    shutil.rmtree(old_folder, ignore_errors=True)
            self.foldername = new_folder_name
            self.save()

        if custom_title != self.__title:
            self.override_title = custom_title
        else:
            self.override_title = ''

    def get_downloaded_episodes(self):
        return self.db.load_episodes(self, factory=self.episode_factory, state=gpodder.STATE_DOWNLOADED)
    
    def get_new_episodes(self, downloading=lambda e: False):
        """
        Get a list of new episodes. You can optionally specify
        "downloading" as a callback that takes an episode as
        a parameter and returns True if the episode is currently
        being downloaded or False if not.

        By default, "downloading" is implemented so that it
        reports all episodes as not downloading.
        """
        return [episode for episode in self.db.load_episodes(self, \
                factory=self.episode_factory) if \
                episode.check_is_new(downloading=downloading)]

    def get_playlist_filename(self):
        # If the save_dir doesn't end with a slash (which it really should
        # not, if the implementation is correct, we can just append .m3u :)
        assert self.save_dir[-1] != '/'
        return self.save_dir+'.m3u'

    def update_m3u_playlist(self):
        m3u_filename = self.get_playlist_filename()

        downloaded_episodes = self.get_downloaded_episodes()
        if not downloaded_episodes:
            log('No episodes - removing %s', m3u_filename, sender=self)
            util.delete_file(m3u_filename)
            return

        log('Writing playlist to %s', m3u_filename, sender=self)
        f = open(m3u_filename, 'w')
        f.write('#EXTM3U\n')

        # Sort downloaded episodes by publication date, ascending
        def older(episode_a, episode_b):
            return cmp(episode_a.pubDate, episode_b.pubDate)

        for episode in sorted(downloaded_episodes, cmp=older):
            if episode.was_downloaded(and_exists=True):
                filename = episode.local_filename(create=False)
                assert filename is not None

                if os.path.dirname(filename).startswith(os.path.dirname(m3u_filename)):
                    filename = filename[len(os.path.dirname(m3u_filename)+os.sep):]
                f.write('#EXTINF:0,'+self.title+' - '+episode.title+' ('+episode.cute_pubdate()+')\n')
                f.write(filename+'\n')

        f.close()

    def addDownloadedItem(self, item):
        log('addDownloadedItem(%s)', item.url)

        if not item.was_downloaded():
            item.mark_downloaded(save=True)
            self.update_m3u_playlist()

    def get_all_episodes(self):
        return self.db.load_episodes(self, factory=self.episode_factory)

    def find_unique_folder_name(self, foldername):
        current_try = util.sanitize_filename(foldername, self.MAX_FOLDERNAME_LENGTH)
        next_try_id = 2

        while True:
            if not os.path.exists(os.path.join(self.download_dir, current_try)):
                self.db.remove_foldername_if_deleted_channel(current_try)

            if self.db.channel_foldername_exists(current_try):
                current_try = '%s (%d)' % (foldername, next_try_id)
                next_try_id += 1
            else:
                return current_try

    def get_save_dir(self):
        urldigest = hashlib.md5(self.url).hexdigest()
        sanitizedurl = util.sanitize_filename(self.url, self.MAX_FOLDERNAME_LENGTH)
        if self.foldername is None or (self.auto_foldername and (self.foldername == urldigest or self.foldername.startswith(sanitizedurl))):
            # we must change the folder name, because it has not been set manually
            fn_template = util.sanitize_filename(self.title, self.MAX_FOLDERNAME_LENGTH)

            # if this is an empty string, try the basename
            if len(fn_template) == 0:
                log('That is one ugly feed you have here! (Report this to bugs.gpodder.org: %s)', self.url, sender=self)
                fn_template = util.sanitize_filename(os.path.basename(self.url), self.MAX_FOLDERNAME_LENGTH)

            # If the basename is also empty, use the first 6 md5 hexdigest chars of the URL
            if len(fn_template) == 0:
                log('That is one REALLY ugly feed you have here! (Report this to bugs.gpodder.org: %s)', self.url, sender=self)
                fn_template = urldigest # no need for sanitize_filename here

            # Find a unique folder name for this podcast
            wanted_foldername = self.find_unique_folder_name(fn_template)

            # if the foldername has not been set, check if the (old) md5 filename exists
            if self.foldername is None and os.path.exists(os.path.join(self.download_dir, urldigest)):
                log('Found pre-0.15.0 download folder for %s: %s', self.title, urldigest, sender=self)
                self.foldername = urldigest

            # we have a valid, new folder name in "current_try" -> use that!
            if self.foldername is not None and wanted_foldername != self.foldername:
                # there might be an old download folder crawling around - move it!
                new_folder_name = os.path.join(self.download_dir, wanted_foldername)
                old_folder_name = os.path.join(self.download_dir, self.foldername)
                if os.path.exists(old_folder_name):
                    if not os.path.exists(new_folder_name):
                        # Old folder exists, new folder does not -> simply rename
                        log('Renaming %s => %s', old_folder_name, new_folder_name, sender=self)
                        os.rename(old_folder_name, new_folder_name)
                    else:
                        # Both folders exist -> move files and delete old folder
                        log('Moving files from %s to %s', old_folder_name, new_folder_name, sender=self)
                        for file in glob.glob(os.path.join(old_folder_name, '*')):
                            shutil.move(file, new_folder_name)
                        log('Removing %s', old_folder_name, sender=self)
                        shutil.rmtree(old_folder_name, ignore_errors=True)
            log('Updating foldername of %s to "%s".', self.url, wanted_foldername, sender=self)
            self.foldername = wanted_foldername
            self.save()

        save_dir = os.path.join(self.download_dir, self.foldername)

        # Create save_dir if it does not yet exist
        if not util.make_directory( save_dir):
            log( 'Could not create save_dir: %s', save_dir, sender = self)

        return save_dir
    
    save_dir = property(fget=get_save_dir)

    def remove_downloaded( self):
        shutil.rmtree( self.save_dir, True)
    
    @property
    def cover_file(self):
        old_cover = os.path.join(self.save_dir, 'cover')
        cover = os.path.join(self.save_dir, '.cover')
        if os.path.exists(old_cover):
            return old_cover
        else:
            return cover

    def delete_episode_by_url(self, url):
        episode = self.db.load_episode(url, factory=self.episode_factory)

        if episode is not None:
            filename = episode.local_filename(create=False)
            if filename is not None:
                util.delete_file(filename)
            else:
                log('Cannot delete episode: %s (I have no filename!)', episode.title, sender=self)
            episode.set_state(gpodder.STATE_DELETED)

        self.update_m3u_playlist()


class PodcastEpisode(PodcastModelObject):
    """holds data for one object in a channel"""
    MAX_FILENAME_LENGTH = 200

    def reload_from_db(self):
        """
        Re-reads all episode details for this object from the
        database and updates this object accordingly. Can be
        used to refresh existing objects when the database has
        been updated (e.g. the filename has been set after a
        download where it was not set before the download)
        """
        d = self.db.load_episode(self.url)
        if d is not None:
            self.update_from_dict(d)

        return self

    @staticmethod
    def from_feedparser_entry( entry, channel):
        episode = PodcastEpisode( channel)

        episode.title = entry.get( 'title', util.get_first_line( util.remove_html_tags( entry.get( 'summary', ''))))
        episode.link = entry.get( 'link', '')
        episode.description = ''

        # Get the episode description (prefer summary, then subtitle)
        for key in ('summary', 'subtitle', 'link'):
            if key in entry:
                episode.description = entry[key]
            if episode.description:
                break

        episode.guid = entry.get( 'id', '')
        if entry.get( 'updated_parsed', None):
            episode.pubDate = rfc822.mktime_tz(entry.updated_parsed+(0,))

        if episode.title == '':
            log( 'Warning: Episode has no title, adding anyways.. (Feed Is Buggy!)', sender = episode)

        enclosure = None
        if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
            enclosure = entry.enclosures[0]
            if len(entry.enclosures) > 1:
                for e in entry.enclosures:
                    if hasattr( e, 'href') and hasattr( e, 'length') and hasattr( e, 'type') and (e.type.startswith('audio/') or e.type.startswith('video/')):
                        if util.normalize_feed_url(e.href) is not None:
                            log( 'Selected enclosure: %s', e.href, sender = episode)
                            enclosure = e
                            break
            episode.url = util.normalize_feed_url( enclosure.get( 'href', ''))
        elif hasattr(entry, 'media_content'):
            media = getattr(entry, 'media_content')
            for m in media:
                if 'url' in m and 'type' in m and (m['type'].startswith('audio/') or m['type'].startswith('video/')):
                    if util.normalize_feed_url(m['url']) is not None:
                        log('Selected media_content: %s', m['url'], sender = episode)
                        episode.url=util.normalize_feed_url(m['url'])
                        episode.mimetype=m['type']
                        if 'fileSize' in m:
                            episode.length=int(m['fileSize'])
                        break
        elif hasattr(entry, 'links'):
            for link in entry.links:
                if not hasattr(link, 'href'):
                    continue

                # YouTube-specific workaround
                if youtube.is_video_link(link.href):
                    episode.url = link.href
                    break

                # Check if we can resolve this link to a audio/video file
                filename, extension = util.filename_from_url(link.href)
                file_type = util.file_type_by_extension(extension)
                if file_type is None and hasattr(link, 'type'):
                    extension = util.extension_from_mimetype(link.type)
                    file_type = util.file_type_by_extension(extension)

                # The link points to a audio or video file - use it!
                if file_type is not None:
                    log('Adding episode with link to file type "%s".', \
                            file_type, sender=episode)
                    episode.url = link.href
                    break

        # Still no luck finding an episode? Try to forcefully scan the
        # HTML/plaintext contents of the entry for MP3 links
        if not episode.url:
            mp3s = re.compile(r'http://[^"]*\.mp3')
            for content in entry.get('content', []):
                html = content.value
                for match in mp3s.finditer(html):
                    episode.url = match.group(0)
                    break
                if episode.url:
                    break

        if not episode.url:
            # This item in the feed has no downloadable enclosure
            return None

        metainfo = None
        if not episode.pubDate:
            metainfo = util.get_episode_info_from_url(episode.url)
            if 'pubdate' in metainfo:
                try:
                    episode.pubDate = int(float(metainfo['pubdate']))
                except:
                    log('Cannot convert pubDate "%s" in from_feedparser_entry.', str(metainfo['pubdate']), traceback=True)

        if hasattr(enclosure, 'length'):
            try:
                episode.length = int(enclosure.length)
                if episode.length == 0:
                    raise ValueError('Zero-length is not acceptable')
            except ValueError, ve:
                log('Invalid episode length: %s (%s)', enclosure.length, ve.message)
                episode.length = -1

        if hasattr( enclosure, 'type'):
            episode.mimetype = enclosure.type

        if episode.title == '':
            ( filename, extension ) = os.path.splitext( os.path.basename( episode.url))
            episode.title = filename

        return episode


    def __init__(self, channel):
        self.db = channel.db
        # Used by Storage for faster saving
        self.id = None
        self.url = ''
        self.title = ''
        self.length = 0
        self.mimetype = 'application/octet-stream'
        self.guid = ''
        self.description = ''
        self.link = ''
        self.channel = channel
        self.pubDate = 0
        self.filename = None
        self.auto_filename = 1 # automatically generated filename

        self.state = gpodder.STATE_NORMAL
        self.is_played = False
        self.is_locked = channel.channel_is_locked

    def save(self):
        if self.state != gpodder.STATE_DOWNLOADED and self.file_exists():
            self.state = gpodder.STATE_DOWNLOADED
        self.db.save_episode(self)

    def set_state(self, state):
        self.state = state
        self.db.mark_episode(self.url, state=self.state, is_played=self.is_played, is_locked=self.is_locked)

    def mark(self, state=None, is_played=None, is_locked=None):
        if state is not None:
            self.state = state
        if is_played is not None:
            self.is_played = is_played
        if is_locked is not None:
            self.is_locked = is_locked
        self.db.mark_episode(self.url, state=state, is_played=is_played, is_locked=is_locked)

    def mark_downloaded(self, save=False):
        self.state = gpodder.STATE_DOWNLOADED
        self.is_played = False
        if save:
            self.save()
            self.db.commit()

    def format_episode_row_markup(self, include_description=False):
        if include_description:
            return '%s\n<small>%s</small>' % (xml.sax.saxutils.escape(self.title),
                    xml.sax.saxutils.escape(self.one_line_description()))
        else:
            return xml.sax.saxutils.escape(self.title)

    @property
    def title_markup(self):
        return self.format_episode_row_markup(False)

    @property
    def maemo_markup(self):
        return ('<b>%s</b>\n<small>%s; '+_('released %s')+ \
                '; '+_('from %s')+'</small>') % (\
                xml.sax.saxutils.escape(self.title), \
                xml.sax.saxutils.escape(self.filesize_prop), \
                xml.sax.saxutils.escape(self.pubdate_prop), \
                xml.sax.saxutils.escape(self.channel.title))

    @property
    def maemo_remove_markup(self):
        if self.is_played:
            played_string = _('played')
        else:
            played_string = _('unplayed')
        downloaded_string = self.get_age_string()
        if not downloaded_string:
            downloaded_string = _('today')
        return ('<b>%s</b>\n<small>%s; %s; '+_('downloaded %s')+ \
                '; '+_('from %s')+'</small>') % (\
                xml.sax.saxutils.escape(self.title), \
                xml.sax.saxutils.escape(self.filesize_prop), \
                xml.sax.saxutils.escape(played_string), \
                xml.sax.saxutils.escape(downloaded_string), \
                xml.sax.saxutils.escape(self.channel.title))

    def age_in_days(self):
        return util.file_age_in_days(self.local_filename(create=False, \
                check_only=True))

    def get_age_string(self):
        return util.file_age_to_string(self.age_in_days())

    age_prop = property(fget=get_age_string)

    def one_line_description( self):
        lines = util.remove_html_tags(self.description).strip().splitlines()
        if not lines or lines[0] == '':
            return _('No description available')
        else:
            return ' '.join(lines)

    def delete_from_disk(self):
        try:
            self.channel.delete_episode_by_url(self.url)
        except:
            log('Cannot delete episode from disk: %s', self.title, traceback=True, sender=self)

    def find_unique_file_name(self, url, filename, extension):
        current_try = util.sanitize_filename(filename, self.MAX_FILENAME_LENGTH)+extension
        next_try_id = 2
        lookup_url = None

        if self.filename == current_try and current_try is not None:
            # We already have this filename - good!
            return current_try

        while self.db.episode_filename_exists(current_try):
            if next_try_id == 2 and not youtube.is_video_link(url):
                # If we arrive here, current_try has a collision, so
                # try to resolve the URL for a better basename
                log('Filename collision: %s - trying to resolve...', current_try, sender=self)
                url = util.get_real_url(self.channel.authenticate_url(url))
                episode_filename, extension_UNUSED = util.filename_from_url(url)
                current_try = util.sanitize_filename(episode_filename, self.MAX_FILENAME_LENGTH)+extension
                if not self.db.episode_filename_exists(current_try) and current_try:
                    log('Filename %s is available - collision resolved.', current_try, sender=self)
                    return current_try
                else:
                    filename = episode_filename
                    log('Continuing search with %s as basename...', filename, sender=self)

            current_try = '%s (%d)%s' % (filename, next_try_id, extension)
            next_try_id += 1

        return current_try

    def local_filename(self, create, force_update=False, check_only=False,
            template=None):
        """Get (and possibly generate) the local saving filename

        Pass create=True if you want this function to generate a
        new filename if none exists. You only want to do this when
        planning to create/download the file after calling this function.

        Normally, you should pass create=False. This will only
        create a filename when the file already exists from a previous
        version of gPodder (where we used md5 filenames). If the file
        does not exist (and the filename also does not exist), this
        function will return None.

        If you pass force_update=True to this function, it will try to
        find a new (better) filename and move the current file if this
        is the case. This is useful if (during the download) you get
        more information about the file, e.g. the mimetype and you want
        to include this information in the file name generation process.

        If check_only=True is passed to this function, it will never try
        to rename the file, even if would be a good idea. Use this if you
        only want to check if a file exists.

        If "template" is specified, it should be a filename that is to
        be used as a template for generating the "real" filename.

        The generated filename is stored in the database for future access.
        """
        ext = self.extension(may_call_local_filename=False).encode('utf-8', 'ignore')

        # For compatibility with already-downloaded episodes, we
        # have to know md5 filenames if they are downloaded already
        urldigest = hashlib.md5(self.url).hexdigest()

        if not create and self.filename is None:
            urldigest_filename = os.path.join(self.channel.save_dir, urldigest+ext)
            if os.path.exists(urldigest_filename):
                # The file exists, so set it up in our database
                log('Recovering pre-0.15.0 file: %s', urldigest_filename, sender=self)
                self.filename = urldigest+ext
                self.auto_filename = 1
                self.save()
                return urldigest_filename
            return None

        # We only want to check if the file exists, so don't try to
        # rename the file, even if it would be reasonable. See also:
        # http://bugs.gpodder.org/attachment.cgi?id=236
        if check_only:
            if self.filename is None:
                return None
            else:
                return os.path.join(self.channel.save_dir, self.filename)

        if self.filename is None or force_update or (self.auto_filename and self.filename == urldigest+ext):
            # Try to find a new filename for the current file
            if template is not None:
                # If template is specified, trust the template's extension
                episode_filename, ext = os.path.splitext(template)
            else:
                episode_filename, extension_UNUSED = util.filename_from_url(self.url)
            fn_template = util.sanitize_filename(episode_filename, self.MAX_FILENAME_LENGTH)

            if 'redirect' in fn_template and template is None:
                # This looks like a redirection URL - force URL resolving!
                log('Looks like a redirection to me: %s', self.url, sender=self)
                url = util.get_real_url(self.channel.authenticate_url(self.url))
                log('Redirection resolved to: %s', url, sender=self)
                (episode_filename, extension_UNUSED) = util.filename_from_url(url)
                fn_template = util.sanitize_filename(episode_filename, self.MAX_FILENAME_LENGTH)

            # Use the video title for YouTube downloads
            for yt_url in ('http://youtube.com/', 'http://www.youtube.com/'):
                if self.url.startswith(yt_url):
                    fn_template = os.path.basename(self.title)

            # If the basename is empty, use the md5 hexdigest of the URL
            if len(fn_template) == 0 or fn_template.startswith('redirect.'):
                log('Report to bugs.gpodder.org: Podcast at %s with episode URL: %s', self.channel.url, self.url, sender=self)
                fn_template = urldigest

            # Find a unique filename for this episode
            wanted_filename = self.find_unique_file_name(self.url, fn_template, ext)

            # We populate the filename field the first time - does the old file still exist?
            if self.filename is None and os.path.exists(os.path.join(self.channel.save_dir, urldigest+ext)):
                log('Found pre-0.15.0 downloaded file: %s', urldigest, sender=self)
                self.filename = urldigest+ext

            # The old file exists, but we have decided to want a different filename
            if self.filename is not None and wanted_filename != self.filename:
                # there might be an old download folder crawling around - move it!
                new_file_name = os.path.join(self.channel.save_dir, wanted_filename)
                old_file_name = os.path.join(self.channel.save_dir, self.filename)
                if os.path.exists(old_file_name) and not os.path.exists(new_file_name):
                    log('Renaming %s => %s', old_file_name, new_file_name, sender=self)
                    os.rename(old_file_name, new_file_name)
                elif force_update and not os.path.exists(old_file_name):
                    # When we call force_update, the file might not yet exist when we
                    # call it from the downloading code before saving the file
                    log('Choosing new filename: %s', new_file_name, sender=self)
                else:
                    log('Warning: %s exists or %s does not.', new_file_name, old_file_name, sender=self)
                log('Updating filename of %s to "%s".', self.url, wanted_filename, sender=self)
            elif self.filename is None:
                log('Setting filename to "%s".', wanted_filename, sender=self)
            else:
                log('Should update filename. Stays the same (%s). Good!', \
                        wanted_filename, sender=self)
            self.filename = wanted_filename
            self.save()
            self.db.commit()

        return os.path.join(self.channel.save_dir, self.filename)

    def set_mimetype(self, mimetype, commit=False):
        """Sets the mimetype for this episode"""
        self.mimetype = mimetype
        if commit:
            self.db.commit()

    def extension(self, may_call_local_filename=True):
        filename, ext = util.filename_from_url(self.url)
        if may_call_local_filename:
            filename = self.local_filename(create=False)
            if filename is not None:
                filename, ext = os.path.splitext(filename)
        # if we can't detect the extension from the url fallback on the mimetype
        if ext == '' or util.file_type_by_extension(ext) is None:
            ext = util.extension_from_mimetype(self.mimetype)
        return ext

    def check_is_new(self, downloading=lambda e: False):
        """
        Returns True if this episode is to be considered new.
        "Downloading" should be a callback that gets an episode
        as its parameter and returns True if the episode is
        being downloaded at the moment.
        """
        return self.state == gpodder.STATE_NORMAL and \
                not self.is_played and \
                not downloading(self)

    def mark_new(self):
        self.state = gpodder.STATE_NORMAL
        self.is_played = False
        self.db.mark_episode(self.url, state=self.state, is_played=self.is_played)

    def mark_old(self):
        self.is_played = True
        self.db.mark_episode(self.url, is_played=True)

    def file_exists(self):
        filename = self.local_filename(create=False, check_only=True)
        if filename is None:
            return False
        else:
            return os.path.exists(filename)

    def was_downloaded(self, and_exists=False):
        if self.state != gpodder.STATE_DOWNLOADED:
            return False
        if and_exists and not self.file_exists():
            return False
        return True

    def sync_filename(self, use_custom=False, custom_format=None):
        if use_custom:
            return util.object_string_formatter(custom_format,
                    episode=self, podcast=self.channel)
        else:
            return self.title

    def file_type( self):
        return util.file_type_by_extension( self.extension() )

    @property
    def basename( self):
        return os.path.splitext( os.path.basename( self.url))[0]
    
    @property
    def published( self):
        """
        Returns published date as YYYYMMDD (or 00000000 if not available)
        """
        try:
            return datetime.datetime.fromtimestamp(self.pubDate).strftime('%Y%m%d')
        except:
            log( 'Cannot format pubDate for "%s".', self.title, sender = self)
            return '00000000'

    @property
    def pubtime(self):
        """
        Returns published time as HHMM (or 0000 if not available)
        """
        try:
            return datetime.datetime.fromtimestamp(self.pubDate).strftime('%H%M')
        except:
            log('Cannot format pubDate (time) for "%s".', self.title, sender=self)
            return '0000'
    
    def cute_pubdate(self):
        result = util.format_date(self.pubDate)
        if result is None:
            return '(%s)' % _('unknown')
        else:
            return result
    
    pubdate_prop = property(fget=cute_pubdate)

    def calculate_filesize( self):
        filename = self.local_filename(create=False)
        if filename is None:
            log('calculate_filesized called, but filename is None!', sender=self)
        try:
            self.length = os.path.getsize(filename)
        except:
            log( 'Could not get filesize for %s.', self.url)

    def get_filesize_string(self):
        return util.format_filesize(self.length)

    filesize_prop = property(fget=get_filesize_string)

    def get_channel_title( self):
        return self.channel.title

    channel_prop = property(fget=get_channel_title)

    def get_played_string( self):
        if not self.is_played:
            return _('Unplayed')
        
        return ''

    played_prop = property(fget=get_played_string)
    
    def is_duplicate( self, episode ):
        if self.title == episode.title and self.pubDate == episode.pubDate:
            log('Possible duplicate detected: %s', self.title)
            return True
        return False

