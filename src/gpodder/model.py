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


#
#  gpodder.model - Core model classes for gPodder (2009-08-13)
#  Based on libpodcasts.py (thp, 2005-10-29)
#

import gpodder
from gpodder import util
from gpodder import feedcore
from gpodder import youtube

from gpodder.liblogger import log

import os
import re
import glob
import shutil
import time
import datetime
import rfc822
import hashlib
import feedparser
import xml.sax.saxutils

_ = gpodder.gettext


class CustomFeed(feedcore.ExceptionWithData): pass

class gPodderFetcher(feedcore.Fetcher):
    """
    This class extends the feedcore Fetcher with the gPodder User-Agent and the
    Proxy handler based on the current settings in gPodder.
    """
    custom_handlers = []

    def __init__(self):
        feedcore.Fetcher.__init__(self, gpodder.user_agent)

    def fetch_channel(self, channel):
        etag = channel.http_etag
        modified = feedparser._parse_date(channel.http_last_modified)
        # If we have a username or password, rebuild the url with them included
        # Note: using a HTTPBasicAuthHandler would be pain because we need to
        # know the realm. It can be done, but I think this method works, too
        url = channel.authenticate_url(channel.url)
        for handler in self.custom_handlers:
            custom_feed = handler.handle_url(url)
            if custom_feed is not None:
                raise CustomFeed(custom_feed)
        self.fetch(url, etag, modified)

    def _resolve_url(self, url):
        return youtube.get_real_channel_url(url)

    @classmethod
    def register(cls, handler):
        cls.custom_handlers.append(handler)

# The "register" method is exposed here for external usage
register_custom_handler = gPodderFetcher.register

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


class PodcastEpisode(PodcastModelObject):
    """holds data for one object in a channel"""
    MAX_FILENAME_LENGTH = 200

    def _get_is_played(self):
        return not self.is_new

    def _set_is_played(self, is_played):
        self.is_new = not is_played

    is_played = property(fget=_get_is_played, fset=_set_is_played)

    def _get_podcast_id(self):
        return self.channel.id

    def _set_podcast_id(self, podcast_id):
        assert self.channel.id == podcast_id

    # Accessor for the "podcast_id" DB column
    podcast_id = property(fget=_get_podcast_id, fset=_set_podcast_id)

    def reload_from_db(self):
        """
        Re-reads all episode details for this object from the
        database and updates this object accordingly. Can be
        used to refresh existing objects when the database has
        been updated (e.g. the filename has been set after a
        download where it was not set before the download)
        """
        d = self.db.load_episode(self.id)
        self.update_from_dict(d or {})
        return self

    def has_website_link(self):
        return bool(self.link) and (self.link != self.url or \
                youtube.is_video_link(self.link))

    @classmethod
    def from_feedparser_entry(cls, entry, channel, mimetype_prefs=''):
        episode = cls(channel)

        # Replace multi-space and newlines with single space (Maemo bug 11173)
        episode.title = re.sub('\s+', ' ', entry.get('title', ''))
        episode.link = entry.get('link', '')
        if 'content' in entry and len(entry['content']) and \
                entry['content'][0].get('type', '') == 'text/html':
            episode.description = entry['content'][0].value
        else:
            episode.description = entry.get('summary', '')

        try:
            # Parse iTunes-specific podcast duration metadata
            total_time = util.parse_time(entry.get('itunes_duration', ''))
            episode.total_time = total_time
        except:
            pass

        # Fallback to subtitle if summary is not available0
        if not episode.description:
            episode.description = entry.get('subtitle', '')

        episode.guid = entry.get('id', '')
        if entry.get('updated_parsed', None):
            episode.published = rfc822.mktime_tz(entry.updated_parsed+(0,))

        enclosures = entry.get('enclosures', ())
        audio_available = any(e.get('type', '').startswith('audio/') \
                for e in enclosures)
        video_available = any(e.get('type', '').startswith('video/') \
                for e in enclosures)

        # Create the list of preferred mime types
        mimetype_prefs = mimetype_prefs.split(',')

        def calculate_preference_value(enclosure):
            """Calculate preference value of an enclosure

            This is based on mime types and allows users to prefer
            certain mime types over others (e.g. MP3 over AAC, ...)
            """
            mimetype = enclosure.get('type', None)
            try:
                # If the mime type is found, return its (zero-based) index
                return mimetype_prefs.index(mimetype)
            except ValueError:
                # If it is not found, assume it comes after all listed items
                return len(mimetype_prefs)

        # Enclosures
        for e in sorted(enclosures, key=calculate_preference_value):
            episode.mime_type = e.get('type', 'application/octet-stream')
            if episode.mime_type == '':
                # See Maemo bug 10036
                log('Fixing empty mimetype in ugly feed', sender=episode)
                episode.mime_type = 'application/octet-stream'

            if '/' not in episode.mime_type:
                continue

            # Skip images in feeds if audio or video is available (bug 979)
            if episode.mime_type.startswith('image/') and \
                    (audio_available or video_available):
                continue

            episode.url = util.normalize_feed_url(e.get('href', ''))
            if not episode.url:
                continue

            try:
                episode.file_size = int(e.length) or -1
            except:
                episode.file_size = -1

            return episode

        # Media RSS content
        for m in entry.get('media_content', ()):
            episode.mime_type = m.get('type', 'application/octet-stream')
            if '/' not in episode.mime_type:
                continue

            episode.url = util.normalize_feed_url(m.get('url', ''))
            if not episode.url:
                continue

            try:
                episode.file_size = int(m.fileSize) or -1
            except:
                episode.file_size = -1

            return episode

        # Brute-force detection of any links
        for l in entry.get('links', ()):
            episode.url = util.normalize_feed_url(l.get('href', ''))
            if not episode.url:
                continue

            if youtube.is_video_link(episode.url):
                return episode

            # Check if we can resolve this link to a audio/video file
            filename, extension = util.filename_from_url(episode.url)
            file_type = util.file_type_by_extension(extension)
            if file_type is None and hasattr(l, 'type'):
                extension = util.extension_from_mimetype(l.type)
                file_type = util.file_type_by_extension(extension)

            # The link points to a audio or video file - use it!
            if file_type is not None:
                return episode

        # Scan MP3 links in description text
        mp3s = re.compile(r'http://[^"]*\.mp3')
        for content in entry.get('content', ()):
            html = content.value
            for match in mp3s.finditer(html):
                episode.url = match.group(0)
                return episode

        return None

    def __init__(self, channel):
        self.db = channel.db
        # Used by Storage for faster saving
        self.id = None
        self.url = ''
        self.title = ''
        self.file_size = 0
        self.mime_type = 'application/octet-stream'
        self.guid = ''
        self.description = ''
        self.link = ''
        self.channel = channel
        self.published = 0
        self.download_filename = None

        self.state = gpodder.STATE_NORMAL
        self.is_new = True
        self.archive = channel.auto_archive_episodes

        # Time attributes
        self.total_time = 0
        self.current_position = 0
        self.current_position_updated = 0

        # Timestamp of last playback time
        self.last_playback = 0

    def get_is_locked(self):
        return self.archive

    def set_is_locked(self, is_locked):
        self.archive = bool(is_locked)

    is_locked = property(fget=get_is_locked, fset=set_is_locked)

    def save(self):
        if self.state != gpodder.STATE_DOWNLOADED and self.file_exists():
            self.state = gpodder.STATE_DOWNLOADED
        if gpodder.user_hooks is not None:
            gpodder.user_hooks.on_episode_save(self)
        self.db.save_episode(self)

    def on_downloaded(self, filename):
        self.state = gpodder.STATE_DOWNLOADED
        self.is_new = True
        self.file_size = os.path.getsize(filename)
        self.save()

    def set_state(self, state):
        self.state = state
        self.db.update_episode_state(self)

    def playback_mark(self):
        self.is_new = False
        self.last_playback = int(time.time())
        self.save()

    def mark(self, state=None, is_played=None, is_locked=None):
        if state is not None:
            self.state = state
        if is_played is not None:
            self.is_new = not is_played
        if is_locked is not None:
            self.is_locked = is_locked
        self.db.update_episode_state(self)

    @property
    def title_markup(self):
        return '%s\n<small>%s</small>' % (xml.sax.saxutils.escape(self.title),
                          xml.sax.saxutils.escape(self.channel.title))

    @property
    def markup_new_episodes(self):
        if self.file_size > 0:
            length_str = '%s; ' % util.format_filesize(self.file_size)
        else:
            length_str = ''
        return ('<b>%s</b>\n<small>%s'+_('released %s')+ \
                '; '+_('from %s')+'</small>') % (\
                xml.sax.saxutils.escape(re.sub('\s+', ' ', self.title)), \
                xml.sax.saxutils.escape(length_str), \
                xml.sax.saxutils.escape(self.pubdate_prop), \
                xml.sax.saxutils.escape(re.sub('\s+', ' ', self.channel.title)))

    @property
    def markup_delete_episodes(self):
        if self.total_time and self.current_position:
            played_string = self.get_play_info_string()
        elif not self.is_new:
            played_string = _('played')
        else:
            played_string = _('unplayed')
        downloaded_string = self.get_age_string()
        if not downloaded_string:
            downloaded_string = _('today')
        return ('<b>%s</b>\n<small>%s; %s; '+_('downloaded %s')+ \
                '; '+_('from %s')+'</small>') % (\
                xml.sax.saxutils.escape(self.title), \
                xml.sax.saxutils.escape(util.format_filesize(self.file_size)), \
                xml.sax.saxutils.escape(played_string), \
                xml.sax.saxutils.escape(downloaded_string), \
                xml.sax.saxutils.escape(self.channel.title))

    def age_in_days(self):
        return util.file_age_in_days(self.local_filename(create=False, \
                check_only=True))

    age_int_prop = property(fget=age_in_days)

    def get_age_string(self):
        return util.file_age_to_string(self.age_in_days())

    age_prop = property(fget=get_age_string)

    def one_line_description(self):
        MAX_LINE_LENGTH = 120
        desc = util.remove_html_tags(self.description or '')
        desc = re.sub('\n', ' ', desc).strip()
        if not desc:
            return _('No description available')
        else:
            if len(desc) > MAX_LINE_LENGTH:
                return desc[:MAX_LINE_LENGTH] + '...'
            else:
                return desc

    def delete_from_disk(self):
        filename = self.local_filename(create=False, check_only=True)
        if filename is not None:
            util.delete_file(filename)

        self.set_state(gpodder.STATE_DELETED)

    def find_unique_file_name(self, url, filename, extension):
        current_try = util.sanitize_filename(filename, self.MAX_FILENAME_LENGTH)+extension
        next_try_id = 2
        lookup_url = None

        if self.download_filename == current_try and current_try is not None:
            # We already have this filename - good!
            return current_try

        while self.db.episode_filename_exists(current_try):
            current_try = '%s (%d)%s' % (filename, next_try_id, extension)
            next_try_id += 1

        return current_try

    def local_filename(self, create, force_update=False, check_only=False,
            template=None, return_wanted_filename=False):
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

        If return_wanted_filename is True, the filename will not be written to
        the database, but simply returned by this function (for use by the
        "import external downloads" feature).
        """
        ext = self.extension(may_call_local_filename=False).encode('utf-8', 'ignore')

        # For compatibility with already-downloaded episodes, we
        # have to know md5 filenames if they are downloaded already
        urldigest = hashlib.md5(self.url).hexdigest()

        if not create and self.download_filename is None:
            return None

        # We only want to check if the file exists, so don't try to
        # rename the file, even if it would be reasonable. See also:
        # http://bugs.gpodder.org/attachment.cgi?id=236
        if check_only:
            if self.download_filename is None:
                return None
            else:
                return os.path.join(self.channel.save_dir, self.download_filename)

        if self.download_filename is None or force_update:
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
                    fn_template = util.sanitize_filename(os.path.basename(self.title), self.MAX_FILENAME_LENGTH)

            # Nicer download filenames for Soundcloud streams
            if fn_template == 'stream':
                sanitized = util.sanitize_filename(self.title, self.MAX_FILENAME_LENGTH)
                if sanitized:
                    fn_template = sanitized

            # If the basename is empty, use the md5 hexdigest of the URL
            if len(fn_template) == 0 or fn_template.startswith('redirect.'):
                log('Report to bugs.gpodder.org: Podcast at %s with episode URL: %s', self.channel.url, self.url, sender=self)
                fn_template = urldigest

            # Find a unique filename for this episode
            wanted_filename = self.find_unique_file_name(self.url, fn_template, ext)

            if return_wanted_filename:
                # return the calculated filename without updating the database
                return wanted_filename

            # We populate the filename field the first time - does the old file still exist?
            if self.download_filename is None and os.path.exists(os.path.join(self.channel.save_dir, urldigest+ext)):
                log('Found pre-0.15.0 downloaded file: %s', urldigest, sender=self)
                self.download_filename = urldigest+ext

            # The old file exists, but we have decided to want a different filename
            if self.download_filename is not None and wanted_filename != self.download_filename:
                # there might be an old download folder crawling around - move it!
                new_file_name = os.path.join(self.channel.save_dir, wanted_filename)
                old_file_name = os.path.join(self.channel.save_dir, self.download_filename)
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
            elif self.download_filename is None:
                log('Setting filename to "%s".', wanted_filename, sender=self)
            else:
                log('Should update filename. Stays the same (%s). Good!', \
                        wanted_filename, sender=self)
            self.download_filename = wanted_filename
            self.save()
            self.db.commit()

        return os.path.join(self.channel.save_dir, self.download_filename)

    def set_mimetype(self, mimetype, commit=False):
        """Sets the mimetype for this episode"""
        self.mime_type = mimetype
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
            ext = util.extension_from_mimetype(self.mime_type)
        return ext

    def check_is_new(self, downloading=lambda e: False):
        """
        Returns True if this episode is to be considered new.
        "Downloading" should be a callback that gets an episode
        as its parameter and returns True if the episode is
        being downloaded at the moment.
        """
        return self.state == gpodder.STATE_NORMAL and \
                self.is_new and \
                not downloading(self)

    def mark_new(self):
        self.state = gpodder.STATE_NORMAL
        self.is_new = True
        self.db.update_episode_state(self)

    def mark_old(self):
        self.is_new = False
        self.db.update_episode_state(self)

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

    def sync_filename(self):
        return self.title

    def file_type(self):
        # Assume all YouTube links are video files
        if youtube.is_video_link(self.url):
            return 'video'

        return util.file_type_by_extension(self.extension())

    @property
    def basename( self):
        return os.path.splitext( os.path.basename( self.url))[0]

    @property
    def pubtime(self):
        """
        Returns published time as HHMM (or 0000 if not available)
        """
        try:
            return datetime.datetime.fromtimestamp(self.published).strftime('%H%M')
        except:
            log('Cannot format published (time) for "%s".', self.title, sender=self)
            return '0000'

    def playlist_title(self):
        """Return a title for this episode in a playlist

        The title will be composed of the podcast name, the
        episode name and the publication date. The return
        value is the canonical representation of this episode
        in playlists (for example, M3U playlists).
        """
        return '%s - %s (%s)' % (self.channel.title, \
                self.title, \
                self.cute_pubdate())

    def cute_pubdate(self):
        result = util.format_date(self.published)
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
            self.file_size = os.path.getsize(filename)
        except:
            log( 'Could not get filesize for %s.', self.url)

    def is_finished(self):
        """Return True if this episode is considered "finished playing"

        An episode is considered "finished" when there is a
        current position mark on the track, and when the
        current position is greater than 99 percent of the
        total time or inside the last 10 seconds of a track.
        """
        return self.current_position > 0 and \
                (self.current_position + 10 >= self.total_time or \
                 self.current_position >= self.total_time*.99)

    def get_play_info_string(self):
        duration = util.format_time(self.total_time)
        if self.current_position > 0 and \
                self.current_position != self.total_time:
            position = util.format_time(self.current_position)
            return '%s / %s' % (position, duration)
        elif self.total_time > 0:
            return duration
        else:
            return '-'

    def is_duplicate(self, episode):
        if self.title == episode.title and self.published == episode.published:
            log('Possible duplicate detected: %s', self.title)
            return True
        return False

    def duplicate_id(self):
        return hash((self.title, self.published))

    def update_from(self, episode):
        for k in ('title', 'url', 'description', 'link', 'published', 'guid', 'file_size'):
            setattr(self, k, getattr(episode, k))




class PodcastChannel(PodcastModelObject):
    """holds data for a complete channel"""
    MAX_FOLDERNAME_LENGTH = 150
    SECONDS_PER_WEEK = 7*24*60*60
    EpisodeClass = PodcastEpisode

    feed_fetcher = gPodderFetcher()

    def import_external_files(self):
        """Check the download folder for externally-downloaded files

        This will try to assign downloaded files with episodes in the
        database and (failing that) will move downloaded files into
        the "Unknown" subfolder in the download directory, so that
        the user knows that gPodder doesn't know to which episode the
        file belongs (the "Unknown" folder may be used by external
        tools or future gPodder versions for better import support).
        """
        known_files = set(e.local_filename(create=False) \
                for e in self.get_downloaded_episodes())
        existing_files = set(filename for filename in \
                glob.glob(os.path.join(self.save_dir, '*')))
        external_files = existing_files.difference(known_files, \
                [os.path.join(self.save_dir, x) \
                for x in ('folder.jpg', 'Unknown')])
        if not external_files:
            return 0

        all_episodes = self.get_all_episodes()

        count = 0
        for filename in external_files:
            found = False

            basename = os.path.basename(filename)
            existing = self.get_episode_by_filename(basename)
            if existing:
                log('Importing external download: %s', filename)
                existing.on_downloaded(filename)
                count += 1
                continue

            for episode in all_episodes:
                wanted_filename = episode.local_filename(create=True, \
                        return_wanted_filename=True)
                if basename == wanted_filename:
                    log('Importing external download: %s', filename)
                    episode.download_filename = basename
                    episode.on_downloaded(filename)
                    count += 1
                    found = True
                    break

                wanted_base, wanted_ext = os.path.splitext(wanted_filename)
                target_base, target_ext = os.path.splitext(basename)
                if wanted_base == target_base:
                    # Filenames only differ by the extension
                    wanted_type = util.file_type_by_extension(wanted_ext)
                    target_type = util.file_type_by_extension(target_ext)

                    # If wanted type is None, assume that we don't know
                    # the right extension before the download (e.g. YouTube)
                    # if the wanted type is the same as the target type,
                    # assume that it's the correct file
                    if wanted_type is None or wanted_type == target_type:
                        log('Importing external download: %s', filename)
                        episode.download_filename = basename
                        episode.on_downloaded(filename)
                        found = True
                        count += 1
                        break

            if not found:
                log('Unknown external file: %s', filename)
                target_dir = os.path.join(self.save_dir, 'Unknown')
                if util.make_directory(target_dir):
                    target_file = os.path.join(target_dir, basename)
                    log('Moving %s => %s', filename, target_file)
                    try:
                        shutil.move(filename, target_file)
                    except Exception, e:
                        log('Could not move file: %s', e, sender=self)

        return count

    @classmethod
    def load_from_db(cls, db):
        return db.load_podcasts(factory=cls.create_from_dict)

    @classmethod
    def load(cls, db, url, create=True, authentication_tokens=None,\
            max_episodes=0, \
            mimetype_prefs=''):
        if isinstance(url, unicode):
            url = url.encode('utf-8')

        tmp = db.load_podcasts(factory=cls.create_from_dict, url=url)
        if len(tmp):
            return tmp[0]
        elif create:
            tmp = cls(db)
            tmp.url = url
            if authentication_tokens is not None:
                tmp.auth_username = authentication_tokens[0]
                tmp.auth_password = authentication_tokens[1]

            tmp.update(max_episodes, mimetype_prefs)

            # Mark episodes as downloaded if files already exist (bug 902)
            tmp.import_external_files()

            tmp.save()
            return tmp

    def episode_factory(self, d, db__parameter_is_unused=None):
        """
        This function takes a dictionary containing key-value pairs for
        episodes and returns a new PodcastEpisode object that is connected
        to this object.

        Returns: A new PodcastEpisode object
        """
        return self.EpisodeClass.create_from_dict(d, self)

    def _consume_custom_feed(self, custom_feed, max_episodes=0):
        self.title = custom_feed.get_title()
        self.link = custom_feed.get_link()
        self.description = custom_feed.get_description()
        self.cover_url = custom_feed.get_image()
        self.published = int(time.time())
        self.save()

        guids = [episode.guid for episode in self.get_all_episodes()]

        # Insert newly-found episodes into the database
        custom_feed.get_new_episodes(self, guids)

        self.save()

        self.db.purge(max_episodes, self.id)

    def _consume_updated_feed(self, feed, max_episodes=0, mimetype_prefs=''):
        self.parse_error = feed.get('bozo_exception', None)

        # Replace multi-space and newlines with single space (Maemo bug 11173)
        self.title = re.sub('\s+', ' ', feed.feed.get('title', self.url))

        self.link = feed.feed.get('link', self.link)
        self.description = feed.feed.get('subtitle', self.description)
        # Start YouTube-specific title FIX
        YOUTUBE_PREFIX = 'Uploads by '
        if self.title.startswith(YOUTUBE_PREFIX):
            self.title = self.title[len(YOUTUBE_PREFIX):] + ' on YouTube'
        # End YouTube-specific title FIX

        try:
            self.published = int(rfc822.mktime_tz(feed.feed.get('updated_parsed', None+(0,))))
        except:
            self.published = int(time.time())

        if hasattr(feed.feed, 'image'):
            for attribute in ('href', 'url'):
                new_value = getattr(feed.feed.image, attribute, None)
                if new_value is not None:
                    log('Found cover art in %s: %s', attribute, new_value)
                    self.cover_url = new_value

        if hasattr(feed.feed, 'icon'):
            self.cover_url = feed.feed.icon

        self.save()

        # Load all episodes to update them properly.
        existing = self.get_all_episodes()

        # We can limit the maximum number of entries that gPodder will parse
        if max_episodes > 0 and len(feed.entries) > max_episodes:
            # We have to sort the entries in descending chronological order,
            # because if the feed lists items in ascending order and has >
            # max_episodes old episodes, new episodes will not be shown.
            # See also: gPodder Bug 1186
            try:
                entries = sorted(feed.entries, \
                        key=lambda x: x.get('updated_parsed', (0,)*9), \
                        reverse=True)[:max_episodes]
            except Exception, e:
                log('Could not sort episodes: %s', e, sender=self, traceback=True)
                entries = feed.entries[:max_episodes]
        else:
            entries = feed.entries

        # Title + PubDate hashes for existing episodes
        existing_dupes = dict((e.duplicate_id(), e) for e in existing)

        # GUID-based existing episode list
        existing_guids = dict((e.guid, e) for e in existing)

        # Get most recent published of all episodes
        last_published = self.db.get_last_published(self) or 0

        # Search all entries for new episodes
        for entry in entries:
            try:
                episode = self.EpisodeClass.from_feedparser_entry(entry, self, mimetype_prefs)
                if episode is not None and not episode.title:
                    episode.title, ext = os.path.splitext(os.path.basename(episode.url))
            except Exception, e:
                log('Cannot instantiate episode: %s. Skipping.', e, sender=self, traceback=True)
                continue

            if episode is None:
                continue

            # Detect (and update) existing episode based on GUIDs
            existing_episode = existing_guids.get(episode.guid, None)
            if existing_episode:
                existing_episode.update_from(episode)
                existing_episode.save()
                continue

            # Detect (and update) existing episode based on duplicate ID
            existing_episode = existing_dupes.get(episode.duplicate_id(), None)
            if existing_episode:
                if existing_episode.is_duplicate(episode):
                    existing_episode.update_from(episode)
                    existing_episode.save()
                    continue

            # Workaround for bug 340: If the episode has been
            # published earlier than one week before the most
            # recent existing episode, do not mark it as new.
            if episode.published < last_published - self.SECONDS_PER_WEEK:
                log('Episode with old date: %s', episode.title, sender=self)
                episode.is_new = False

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

    def _update_etag_modified(self, feed):
        self.http_etag = feed.headers.get('etag', self.http_etag)
        self.http_last_modified = feed.headers.get('last-modified', self.http_last_modified)

    def update(self, max_episodes=0, mimetype_prefs=''):
        try:
            self.feed_fetcher.fetch_channel(self)
        except CustomFeed, updated:
            custom_feed = updated.data
            self._consume_custom_feed(custom_feed, max_episodes)
            self.save()
        except feedcore.UpdatedFeed, updated:
            feed = updated.data
            self._consume_updated_feed(feed, max_episodes, mimetype_prefs)
            self._update_etag_modified(feed)
            self.save()
        except feedcore.NewLocation, updated:
            feed = updated.data
            self.url = feed.href
            self._consume_updated_feed(feed, max_episodes, mimetype_prefs)
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

        if gpodder.user_hooks is not None:
            gpodder.user_hooks.on_podcast_updated(self)

        self.db.commit()

    def delete(self):
        self.db.delete_podcast(self)

    def save(self):
        if gpodder.user_hooks is not None:
            gpodder.user_hooks.on_podcast_save(self)
        if self.download_folder is None:
            # get_save_dir() finds a unique value for download_folder
            self.get_save_dir()
        self.db.save_podcast(self)

    def get_statistics(self):
        if self.id is None:
            return (0, 0, 0, 0, 0)
        else:
            return self.db.get_podcast_statistics(self.id)

    def _get_content_type(self):
        if 'youtube.com' in self.url:
            return 'video'

        content_types = self.db.get_content_types(self.id)
        result = ' and '.join(sorted(set(x.split('/')[0].lower() for x in content_types if not x.startswith('application'))))
        if result == '':
            return 'other'
        return result

    def authenticate_url(self, url):
        return util.url_add_authentication(url, self.auth_username, self.auth_password)

    def __init__(self, db):
        self.db = db
        self.id = None
        self.url = None
        self.title = ''
        self.link = ''
        self.description = ''
        self.cover_url = None
        self.published = 0
        self.parse_error = None

        self.auth_username = ''
        self.auth_password = ''

        self.http_last_modified = None
        self.http_etag = None

        self.auto_archive_episodes = False
        self.download_folder = None
        self.pause_subscription = False

    def _get_cover_url(self):
        return self.cover_url

    image = property(_get_cover_url)

    def get_title( self):
        if not self.__title.strip():
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
        if custom_title == self.title:
            return

        # make sure self.download_folder is initialized
        self.get_save_dir()

        # rename folder if custom_title looks sane
        new_folder_name = self.find_unique_folder_name(custom_title)
        if len(new_folder_name) > 0 and new_folder_name != self.download_folder:
            log('Changing download_folder based on custom title: %s', custom_title, sender=self)
            new_folder = os.path.join(gpodder.downloads, new_folder_name)
            old_folder = os.path.join(gpodder.downloads, self.download_folder)
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
            self.download_folder = new_folder_name
            self.save()

        self.title = custom_title

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
                factory=self.episode_factory, state=gpodder.STATE_NORMAL) if \
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
        util.write_m3u_playlist(m3u_filename, \
                Model.sort_episodes_by_pubdate(downloaded_episodes))

    def get_episode_by_url(self, url):
        return self.db.load_single_episode(self, \
                factory=self.episode_factory, url=url)

    def get_episode_by_filename(self, filename):
        return self.db.load_single_episode(self, \
                factory=self.episode_factory, \
                download_filename=filename)

    def get_all_episodes(self):
        return self.db.load_episodes(self, factory=self.episode_factory)

    def find_unique_folder_name(self, download_folder):
        # Remove trailing dots to avoid errors on Windows (bug 600)
        download_folder = download_folder.strip().rstrip('.')

        current_try = util.sanitize_filename(download_folder, \
                self.MAX_FOLDERNAME_LENGTH)
        next_try_id = 2

        while True:
            if self.db.podcast_download_folder_exists(current_try):
                current_try = '%s (%d)' % (download_folder, next_try_id)
                next_try_id += 1
            else:
                return current_try

    def get_save_dir(self):
        urldigest = hashlib.md5(self.url).hexdigest()
        sanitizedurl = util.sanitize_filename(self.url, self.MAX_FOLDERNAME_LENGTH)
        if self.download_folder is None:
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
            wanted_download_folder = self.find_unique_folder_name(fn_template)

            # if the download_folder has not been set, check if the (old) md5 filename exists
            if self.download_folder is None and os.path.exists(os.path.join(gpodder.downloads, urldigest)):
                log('Found pre-0.15.0 download folder for %s: %s', self.title, urldigest, sender=self)
                self.download_folder = urldigest

            # we have a valid, new folder name in "current_try" -> use that!
            if self.download_folder is not None and wanted_download_folder != self.download_folder:
                # there might be an old download folder crawling around - move it!
                new_folder_name = os.path.join(gpodder.downloads, wanted_download_folder)
                old_folder_name = os.path.join(gpodder.downloads, self.download_folder)
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
            log('Updating download_folder of %s to "%s".', self.url, wanted_download_folder, sender=self)
            self.download_folder = wanted_download_folder
            self.save()

        save_dir = os.path.join(gpodder.downloads, self.download_folder)

        # Create save_dir if it does not yet exist
        if not util.make_directory( save_dir):
            log( 'Could not create save_dir: %s', save_dir, sender = self)

        return save_dir
    
    save_dir = property(fget=get_save_dir)

    def remove_downloaded(self):
        # Remove the playlist file if it exists
        m3u_filename = self.get_playlist_filename()
        if os.path.exists(m3u_filename):
            util.delete_file(m3u_filename)

        # Remove the download directory
        shutil.rmtree(self.save_dir, True)

    @property
    def cover_file(self):
        return os.path.join(self.save_dir, 'folder.jpg')


class Model(object):
    PodcastClass = PodcastChannel

    @classmethod
    def get_podcasts(cls, db):
        return cls.PodcastClass.load_from_db(db)

    @classmethod
    def load_podcast(cls, db, url, create=True, authentication_tokens=None, \
            max_episodes=0, mimetype_prefs=''):
        return cls.PodcastClass.load(db, url, create, authentication_tokens, \
                max_episodes, mimetype_prefs)

    @staticmethod
    def sort_episodes_by_pubdate(episodes, reverse=False):
        """Sort a list of PodcastEpisode objects chronologically

        Returns a iterable, sorted sequence of the episodes
        """
        get_key = lambda e: e.published
        return sorted(episodes, key=get_key, reverse=reverse)

