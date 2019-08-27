# -*- coding: utf-8 -*-
# Manage Youtube subscriptions using youtube-dl (https://github.com/ytdl-org/youtube-dl)
# Requirements: youtube-dl module (pip install youtube_dl)
# (c) 2019-08-17 Eric Le Lay <elelay.fr:contact>
# Released under the same license terms as gPodder itself.

import logging
import os
import re
import time

import youtube_dl
from youtube_dl.utils import sanitize_url

import gpodder
from gpodder import download, feedcore, model, registry, youtube
from gpodder.util import mimetype_from_extension, remove_html_tags

_ = gpodder.gettext


logger = logging.getLogger(__name__)


__title__ = 'youtube-dl'
__description__ = 'Manage Youtube subscriptions using youtube-dl (pip install youtube_dl)'
__only_for__ = 'gtk, cli'
__authors__ = 'Eric Le Lay <elelay.fr:contact>'
__doc__ = 'https://github.com/gpodder/gpodder/blob/master/share/gpodder/extensions/youtube-dl.py'

DefaultConfig = {
    # youtube-dl downloads and parses each video page to get informations about it, which is very slow.
    # Set to False to fall back to the fast but limited (only 15 episodes) gpodder code
    'manage_channel': True,
    # If for some reason youtube-dl download doesn't work for you, you can fallback to gpodder code.
    # Set to False to fall back to default gpodder code (less available formats).
    'manage_downloads': True,
}


# youtube feed still preprocessed by youtube.py (compat)
CHANNEL_RE = re.compile(r'''https://www.youtube.com/feeds/videos.xml\?channel_id=(.+)''')
PLAYLIST_RE = re.compile(r'''https://www.youtube.com/feeds/videos.xml\?playlist_id=(.+)''')


def youtube_parsedate(s):
    """Parse a string into a unix timestamp

    Only strings provided by Youtube-dl API are
    parsed with this function (20170920).
    """
    if s:
        return time.mktime(time.strptime(s, "%Y%m%d"))
    return 0


def video_guid(video_id):
    """
    generate same guid as youtube
    """
    return 'yt:video:{}'.format(video_id)


class YoutubeCustomDownload(download.CustomDownload):
    """
    Represents the download of a single episode using youtube-dl.

    Actual youtube-dl interaction via gPodderYoutubeDL.
    """
    def __init__(self, ytdl, url):
        self._ytdl = ytdl
        self._url = url
        self._reporthook = None

    def retrieve_resume(self, tempname, reporthook=None):
        """
        called by download.DownloadTask to perform the download.
        """
        self._reporthook = reporthook
        res = self._ytdl.fetch_video(self._url, tempname, self._my_hook)
        headers = {}
        # youtube-dl doesn't return a content-type but an extension
        if 'ext' in res:
            ext_filetype = mimetype_from_extension('.{}'.format(res['ext']))
            if ext_filetype:
                headers['content-type'] = ext_filetype
        return headers, res.get('url', self._url)

    def _my_hook(self, d):
        if d['status'] == 'downloading':
            if self._reporthook:
                dl_bytes = d['downloaded_bytes']
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                self._reporthook(dl_bytes, 1, total_bytes)
        elif d['status'] == 'finished':
            if self._reporthook:
                dl_bytes = d['downloaded_bytes']
                self._reporthook(dl_bytes, 1, dl_bytes)
        elif d['status'] == 'error':
            logger.error('download hook error: %r', d)
        else:
            logger.debug('unknown download hook status: %r', d)


class YoutubeFeed(model.Feed):
    """
    Represents the youtube feed for model.PodcastChannel
    """
    def __init__(self, url, cover_url, description, max_episodes, ie_result, downloader):
        self._url = url
        self._cover_url = cover_url
        self._description = description
        self._max_episodes = max_episodes
        ie_result['entries'] = self._process_entries(ie_result.get('entries', []))
        self._ie_result = ie_result
        self._downloader = downloader

    def _process_entries(self, entries):
        filtered_entries = []
        for e in entries:  # consumes the generator!
            if e.get('_type', 'video') == 'url' and e.get('ie_key') == 'Youtube':
                e['guid'] = video_guid(e['id'])
                filtered_entries.append(e)
            else:
                logger.debug('dropping entry not youtube video %r', e)
        return filtered_entries

    def get_title(self):
        return '{} (Youtube)'.format(self._ie_result.get('title') or self._ie_result.get('id') or self._url)

    def get_link(self):
        return self._ie_result.get('webpage_url')

    def get_description(self):
        return self._description

    def get_cover_url(self):
        return self._cover_url

    def get_http_etag(self):
        """ :return str: optional -- last HTTP etag header, for conditional request next time """
        # youtube-dl doesn't provide it!
        return None

    def get_http_last_modified(self):
        """ :return str: optional -- last HTTP Last-Modified header, for conditional request next time """
        # youtube-dl doesn't provide it!
        return None

    def get_new_episodes(self, channel, existing_guids):
        # entries are already sorted by decreasing date
        # trim guids to max episodes
        entries = [e for i, e in enumerate(self._ie_result['entries'])
                   if not self._max_episodes or i < self._max_episodes]
        all_seen_guids = set(e['guid'] for e in entries)
        # only fetch new ones from youtube since they are so slow to get
        new_entries = [e for e in entries if e['guid'] not in existing_guids]
        logger.debug('%i/%i new entries', len(new_entries), len(all_seen_guids))
        self._ie_result['entries'] = new_entries
        self._downloader.refresh_entries(self._ie_result, self._max_episodes)
        # episodes from entries
        episodes = []
        for en in self._ie_result['entries']:
            guid = video_guid(en['id'])
            description = remove_html_tags(en.get('description') or _('No description available'))
            html_description = self.nice_html_description(en, description)
            if en.get('ext'):
                mime_type = mimetype_from_extension('.{}'.format(en['ext']))
            else:
                mime_type = 'application/octet-stream'
            ep = {
                'title': en.get('title', guid),
                'link': en.get('webpage_url'),
                'description': description,
                'description_html': html_description,
                'url': en.get('webpage_url'),
                'file_size': int(en.get('filesize') or 0),
                'mime_type': mime_type,
                'guid': guid,
                'published': youtube_parsedate(en.get('upload_date', None)),
            }
            episode = channel.episode_factory(ep)
            episode.save()
            episodes.append(episode)
        return episodes, all_seen_guids

    def get_next_page(self, channel, max_episodes):
        """
        Paginated feed support (RFC 5005).
        If the feed is paged, return the next feed page.
        Returned page will in turn be asked for the next page, until None is returned.
        :return feedcore.Result: the next feed's page,
                                 as a fully parsed Feed or None
        """
        return None

    @staticmethod
    def nice_html_description(en, description):
        """
        basic html formating + hyperlink highlighting + video thumbnail
        """
        description = re.sub(r'''https?://[^\s]+''',
                             r'''<a href="\g<0>">\g<0></a>''',
                             description)
        description = description.replace('\n', '<br>')
        html = """<style type="text/css">
        body > img { float: left; max-width: 30vw; margin: 0 1em 1em 0; }
        </style>
        """
        img = en.get('thumbnail')
        if img:
            html += '<img src="{}">'.format(img)
        html += '<p>{}</p>'.format(description)
        return html


class gPodderYoutubeDL(download.CustomDownloader):
    def __init__(self, gpodder_config=None):
        self.gpodder_config = gpodder_config
        # cachedir is not much used in youtube-dl, but set it anyway
        cachedir = os.path.join(gpodder.home, 'youtube-dl')
        os.makedirs(cachedir, exist_ok=True)
        self._ydl_opts = {
            'cachedir': cachedir,
            'no_color': True,  # prevent escape codes in desktop notifications on errors
        }

    def add_format(self, gpodder_config, opts):
        """ construct youtube-dl -f argument from configured format. """
        # You can set a custom format or custom formats by editing the config for key
        # `youtube.preferred_fmt_ids`
        #
        # It takes a list of format strings separated by comma: bestaudio, 18
        # they are translated to youtube dl format bestaudio/18, meaning preferably
        # the best audio quality (audio-only) and MP4 360p if it's not available.
        #
        # See https://github.com/ytdl-org/youtube-dl#format-selection for details
        # about youtube-dl format specification.
        fmt_ids = youtube.get_fmt_ids(gpodder_config.youtube)
        opts['format'] = '/'.join(str(fmt) for fmt in fmt_ids)

    def fetch_video(self, url, tempname, reporthook):
        opts = {
            'outtmpl': tempname,  # use given tempname by DownloadTask
            'nopart': True,  # don't append .part (already .partial)
            'retries': 3,  # retry a few times
            'progress_hooks': [reporthook]  # to notify UI
        }
        opts.update(self._ydl_opts)
        self.add_format(self.gpodder_config, opts)
        with youtube_dl.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=True)

    def refresh_entries(self, ie_result, max_episodes):
        # only interested in video metadata
        opts = {
            'skip_download': True,  # don't download the video
            'youtube_include_dash_manifest': False,  # don't download the DASH manifest
        }
        self.add_format(self.gpodder_config, opts)
        opts.update(self._ydl_opts)
        with youtube_dl.YoutubeDL(opts) as ydl:
            ydl.process_ie_result(ie_result, download=False)

    def refresh(self, url, channel_url, max_episodes):
        """
        Fetch a channel or playlist contents.

        Doesn't yet fetch video entry informations, so we only get the video id and title.
        """
        # Duplicate a bit of the YoutubeDL machinery here because we only
        # want to parse the channel/playlist first, not to fetch video entries.
        # We call YoutubeDL.extract_info(process=False), so we
        # have to call extract_info again ourselves when we get a result of type 'url'.
        def extract_type(ie_result):
            result_type = ie_result.get('_type', 'video')
            if result_type not in ('url', 'playlist', 'multi_video'):
                raise Exception('Unsuported result_type: {}'.format(result_type))
            has_playlist = result_type in ('playlist', 'multi_video')
            return result_type, has_playlist

        opts = {
            'youtube_include_dash_manifest': False,  # only interested in video title and id
        }
        opts.update(self._ydl_opts)
        with youtube_dl.YoutubeDL(opts) as ydl:
            ie_result = ydl.extract_info(url, download=False, process=False)
            result_type, has_playlist = extract_type(ie_result)
            while not has_playlist:
                if result_type in ('url', 'url_transparent'):
                    ie_result['url'] = sanitize_url(ie_result['url'])
                if result_type == 'url':
                    logger.debug("extract_info(%s) to get the video list", ie_result['url'])
                    # We have to add extra_info to the results because it may be
                    # contained in a playlist
                    ie_result = ydl.extract_info(ie_result['url'],
                                                 download=False,
                                                 process=False,
                                                 ie_key=ie_result.get('ie_key'))
                result_type, has_playlist = extract_type(ie_result)
        cover_url = youtube.get_cover(channel_url)  # youtube-dl doesn't provide the cover url!
        description = youtube.get_channel_desc(channel_url) # youtube-dl doesn't provide the description!
        return feedcore.Result(feedcore.UPDATED_FEED,
            YoutubeFeed(url, cover_url, description, max_episodes, ie_result, self))

    def fetch_channel(self, channel, max_episodes=0):
        """
        called by model.gPodderFetcher to get a custom feed.
        :returns feedcore.Result: a YoutubeFeed or None if channel is not a youtube channel or playlist
        """
        url = None
        m = CHANNEL_RE.match(channel.url)
        if m:
            url = 'https://www.youtube.com/channel/{}'.format(m.group(1))
        else:
            m = PLAYLIST_RE.match(channel.url)
            if m:
                url = 'https://www.youtube.com/playlist?list={}'.format(m.group(1))
        if url:
            logger.info('Youtube-dl Handling %s => %s', channel.url, url)
            return self.refresh(url, channel.url, max_episodes)
        return None

    def custom_downloader(self, unused_config, episode):
        """
        called from registry.custom_downloader.resolve
        """
        if re.match(r'''https://www.youtube.com/watch\?v=.+''', episode.url):
            return YoutubeCustomDownload(self, episode.url)
        elif re.match(r'''https://www.youtube.com/watch\?v=.+''', episode.link):
            return YoutubeCustomDownload(self, episode.link)
        return None


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_load(self):
        self.ytdl = gPodderYoutubeDL(self.container.manager.core.config)
        logger.info('Registering youtube-dl.')
        if self.container.config.manage_channel:
            registry.feed_handler.register(self.ytdl.fetch_channel)
        if self.container.config.manage_downloads:
            registry.custom_downloader.register(self.ytdl.custom_downloader)

    def on_unload(self):
        logger.info('Unregistering youtube-dl.')
        try:
            registry.feed_handler.unregister(self.ytdl.fetch_channel)
        except ValueError:
            pass
        try:
            registry.custom_downloader.unregister(self.ytdl.custom_downloader)
        except ValueError:
            pass
