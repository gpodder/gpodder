# -*- coding: utf-8 -*-
# Manage YouTube subscriptions using youtube-dl (https://github.com/ytdl-org/youtube-dl)
# Requirements: youtube-dl module (pip install youtube_dl)
# (c) 2019-08-17 Eric Le Lay <elelay.fr:contact>
# Released under the same license terms as gPodder itself.

import logging
import os
import re
import sys
import time
from collections.abc import Iterable

try:
    import yt_dlp as youtube_dl
    program_name = 'yt-dlp'
    want_ytdl_version = '2023.06.22'
except:
    import youtube_dl
    program_name = 'youtube-dl'
    want_ytdl_version = '2023.02.17'  # youtube-dl has been patched, but not yet released

import gpodder
from gpodder import download, feedcore, model, registry, util, youtube

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip

_ = gpodder.gettext


logger = logging.getLogger(__name__)


__title__ = 'youtube-dl'
__description__ = _('Manage YouTube subscriptions using youtube-dl (pip install youtube_dl) or yt-dlp (pip install yt-dlp)')
__only_for__ = 'gtk, cli'
__authors__ = 'Eric Le Lay <elelay.fr:contact>'
__doc__ = 'https://gpodder.github.io/docs/extensions/youtubedl.html'

want_ytdl_version_msg = _('Your version of youtube-dl/yt-dlp %(have_version)s has known issues, please upgrade to %(want_version)s or newer.')

DefaultConfig = {
    # youtube-dl downloads and parses each video page to get information about it, which is very slow.
    # Set to False to fall back to the fast but limited (only 15 episodes) gpodder code
    'manage_channel': True,
    # If for some reason youtube-dl download doesn't work for you, you can fallback to gpodder code.
    # Set to False to fall back to default gpodder code (less available formats).
    'manage_downloads': True,
    # Embed all available subtitles to downloaded videos. Needs ffmpeg.
    'embed_subtitles': False,
}


# youtube feed still preprocessed by youtube.py (compat)
CHANNEL_RE = re.compile(r'''https://www.youtube.com/feeds/videos.xml\?channel_id=(.+)''')
USER_RE = re.compile(r'''https://www.youtube.com/feeds/videos.xml\?user=(.+)''')
PLAYLIST_RE = re.compile(r'''https://www.youtube.com/feeds/videos.xml\?playlist_id=(.+)''')


def youtube_parsedate(s):
    """Parse a string into a unix timestamp

    Only strings provided by youtube-dl API are
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
    def __init__(self, ytdl, url, episode):
        self._ytdl = ytdl
        self._url = url
        self._reporthook = None
        self._prev_dl_bytes = 0
        self._episode = episode
        self._partial_filename = None

    @property
    def partial_filename(self):
        return self._partial_filename

    @partial_filename.setter
    def partial_filename(self, val):
        self._partial_filename = val

    def retrieve_resume(self, tempname, reporthook=None):
        """
        called by download.DownloadTask to perform the download.
        """
        self._reporthook = reporthook
        # outtmpl: use given tempname by DownloadTask
        # (escape % because outtmpl used as a string template by youtube-dl)
        outtmpl = tempname.replace('%', '%%')
        info, opts = self._ytdl.fetch_info(self._url, outtmpl, self._my_hook)
        if program_name == 'yt-dlp':
            default = opts['outtmpl']['default'] if isinstance(opts['outtmpl'], dict) else opts['outtmpl']
            self.partial_filename = os.path.join(opts['paths']['home'], default) % info
        elif program_name == 'youtube-dl':
            self.partial_filename = opts['outtmpl'] % info

        res = self._ytdl.fetch_video(info, opts)
        if program_name == 'yt-dlp':
            # yt-dlp downloads to whatever file name it wants, so rename
            filepath = res.get('requested_downloads', [{}])[0].get('filepath')
            if filepath is None:
                raise Exception("Could not determine youtube-dl output file")
            if filepath != tempname:
                logger.debug('yt-dlp downloaded to "%s" instead of "%s", moving',
                             os.path.basename(filepath),
                             os.path.basename(tempname))
                os.remove(tempname)
                os.rename(filepath, tempname)

        if 'duration' in res and res['duration']:
            self._episode.total_time = res['duration']
        headers = {}
        # youtube-dl doesn't return a content-type but an extension
        if 'ext' in res:
            dot_ext = '.{}'.format(res['ext'])
            if program_name == 'youtube-dl':
                # See #673 when merging multiple formats, the extension is appended to the tempname
                # by youtube-dl resulting in empty .partial file + .partial.mp4 exists
                # and #796 .mkv is chosen by ytdl sometimes
                for try_ext in (dot_ext, ".mp4", ".m4a", ".webm", ".mkv"):
                    tempname_with_ext = tempname + try_ext
                    if os.path.isfile(tempname_with_ext):
                        logger.debug('youtube-dl downloaded to "%s" instead of "%s", moving',
                                     os.path.basename(tempname_with_ext),
                                     os.path.basename(tempname))
                        os.remove(tempname)
                        os.rename(tempname_with_ext, tempname)
                        dot_ext = try_ext
                        break

            ext_filetype = util.mimetype_from_extension(dot_ext)
            if ext_filetype:
                # YouTube weba formats have a webm extension and get a video/webm mime-type
                # but audio content has no width or height, so change it to audio/webm for correct icon and player
                if ext_filetype.startswith('video/') and ('height' not in res or res['height'] is None):
                    ext_filetype = ext_filetype.replace('video/', 'audio/')
                headers['content-type'] = ext_filetype
        return headers, res.get('url', self._url)

    def _my_hook(self, d):
        if d['status'] == 'downloading':
            if self._reporthook:
                dl_bytes = d['downloaded_bytes']
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                self._reporthook(self._prev_dl_bytes + dl_bytes,
                                 1,
                                 self._prev_dl_bytes + total_bytes)
        elif d['status'] == 'finished':
            dl_bytes = d['downloaded_bytes']
            self._prev_dl_bytes += dl_bytes
            if self._reporthook:
                self._reporthook(self._prev_dl_bytes, 1, self._prev_dl_bytes)
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
        seen_guids = set()
        for i, e in enumerate(entries):  # consumes the generator!
            if e.get('_type', 'video') in ('url', 'url_transparent') and e.get('ie_key') == 'Youtube':
                guid = video_guid(e['id'])
                e['guid'] = guid
                if guid in seen_guids:
                    logger.debug('dropping already seen entry %s title="%s"', guid, e.get('title'))
                else:
                    filtered_entries.append(e)
                    seen_guids.add(guid)
            else:
                logger.debug('dropping entry not youtube video %r', e)
            if len(filtered_entries) == self._max_episodes:
                # entries is a generator: stopping now prevents it to download more pages
                logger.debug('stopping entry enumeration')
                break
        return filtered_entries

    def get_title(self):
        return '{} (YouTube)'.format(self._ie_result.get('title') or self._ie_result.get('id') or self._url)

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
        self._downloader.refresh_entries(self._ie_result)
        # episodes from entries
        episodes = []
        for en in self._ie_result['entries']:
            guid = video_guid(en['id'])
            if en.get('ext'):
                mime_type = util.mimetype_from_extension('.{}'.format(en['ext']))
            else:
                mime_type = 'application/octet-stream'
            if en.get('filesize'):
                filesize = int(en['filesize'] or 0)
            else:
                filesize = sum(int(f.get('filesize') or 0)
                               for f in en.get('requested_formats', []))
            ep = {
                'title': en.get('title', guid),
                'link': en.get('webpage_url'),
                'episode_art_url': en.get('thumbnail'),
                'description': util.remove_html_tags(en.get('description') or ''),
                'description_html': '',
                'url': en.get('webpage_url'),
                'file_size': filesize,
                'mime_type': mime_type,
                'guid': guid,
                'published': youtube_parsedate(en.get('upload_date', None)),
                'total_time': int(en.get('duration') or 0),
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


class gPodderYoutubeDL(download.CustomDownloader):
    def __init__(self, gpodder_config, my_config, force=False):
        """
        :param force: force using this downloader even if config says don't manage downloads
        """
        self.gpodder_config = gpodder_config
        self.my_config = my_config
        self.force = force
        # cachedir is not much used in youtube-dl, but set it anyway
        cachedir = os.path.join(gpodder.home, 'youtube-dl')
        os.makedirs(cachedir, exist_ok=True)
        self._ydl_opts = {
            'cachedir': cachedir,
            'noprogress': True,  # prevent progress bar from appearing in console
        }
        # prevent escape codes in desktop notifications on errors
        if program_name == 'yt-dlp':
            self._ydl_opts['color'] = 'no_color'
        else:
            self._ydl_opts['no_color'] = True

        if gpodder.verbose:
            self._ydl_opts['verbose'] = True
        else:
            self._ydl_opts['quiet'] = True
        # Don't create downloaders for URLs supported by these youtube-dl extractors
        self.ie_blacklist = ["Generic"]
        # Cache URL regexes from youtube-dl matches here, seed with youtube regex
        self.regex_cache = [(re.compile(r'https://www.youtube.com/watch\?v=.+'),)]
        # #686 on windows without a console, sys.stdout is None, causing exceptions
        # when adding podcasts.
        # See https://docs.python.org/3/library/sys.html#sys.__stderr__ Note
        if not sys.stdout:
            logger.debug('no stdout, setting youtube-dl logger')
            self._ydl_opts['logger'] = logger

    def add_format(self, gpodder_config, opts, fallback=None):
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
        fmt_ids = youtube.get_fmt_ids(gpodder_config.youtube, False)
        opts['format'] = '/'.join(str(fmt) for fmt in fmt_ids)
        if fallback:
            opts['format'] += '/' + fallback
        logger.debug('format=%s', opts['format'])

    def fetch_info(self, url, tempname, reporthook):
        subs = self.my_config.embed_subtitles
        opts = {
            'paths': {'home': os.path.dirname(tempname)},
            # Postprocessing in yt-dlp breaks without ext
            'outtmpl': (os.path.basename(tempname) if program_name == 'yt-dlp'
                        else tempname) + '.%(ext)s',
            'nopart': True,  # don't append .part (already .partial)
            'retries': 3,  # retry a few times
            'progress_hooks': [reporthook],  # to notify UI
            'writesubtitles': subs,
            'subtitleslangs': ['all'] if subs else [],
            'postprocessors': [{'key': 'FFmpegEmbedSubtitle'}] if subs else [],
        }
        opts.update(self._ydl_opts)
        self.add_format(self.gpodder_config, opts)
        with youtube_dl.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info, opts

    def fetch_video(self, info, opts):
        with youtube_dl.YoutubeDL(opts) as ydl:
            return ydl.process_video_result(info, download=True)

    def refresh_entries(self, ie_result):
        # only interested in video metadata
        opts = {
            'skip_download': True,  # don't download the video
            'youtube_include_dash_manifest': False,  # don't download the DASH manifest
        }
        self.add_format(self.gpodder_config, opts, fallback='18')
        opts.update(self._ydl_opts)
        new_entries = []
        # refresh videos one by one to catch single videos blocked by youtube
        for e in ie_result.get('entries', []):
            tmp = {k: v for k, v in ie_result.items() if k != 'entries'}
            tmp['entries'] = [e]
            try:
                with youtube_dl.YoutubeDL(opts) as ydl:
                    ydl.process_ie_result(tmp, download=False)
                    new_entries.extend(tmp.get('entries'))
            except youtube_dl.utils.DownloadError as ex:
                if ex.exc_info[0] == youtube_dl.utils.ExtractorError:
                    # for instance "This video contains content from xyz, who has blocked it on copyright grounds"
                    logger.warning('Skipping %s: %s', e.get('title', ''), ex.exc_info[1])
                    continue
                logger.exception('Skipping %r: %s', tmp, ex.exc_info)
        ie_result['entries'] = new_entries

    def refresh(self, url, channel_url, max_episodes):
        """
        Fetch a channel or playlist contents.

        Doesn't yet fetch video entry information, so we only get the video id and title.
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
                    ie_result['url'] = youtube_dl.utils.sanitize_url(ie_result['url'])
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
        description = youtube.get_channel_desc(channel_url)  # youtube-dl doesn't provide the description!
        return feedcore.Result(feedcore.UPDATED_FEED,
            YoutubeFeed(url, cover_url, description, max_episodes, ie_result, self))

    def fetch_channel(self, channel, max_episodes=0):
        """
        called by model.gPodderFetcher to get a custom feed.
        :returns feedcore.Result: a YoutubeFeed or None if channel is not a youtube channel or playlist
        """
        if not self.my_config.manage_channel:
            return None
        url = None
        m = CHANNEL_RE.match(channel.url)
        if m:
            url = 'https://www.youtube.com/channel/{}/videos'.format(m.group(1))
        else:
            m = USER_RE.match(channel.url)
            if m:
                url = 'https://www.youtube.com/user/{}/videos'.format(m.group(1))
            else:
                m = PLAYLIST_RE.match(channel.url)
                if m:
                    url = 'https://www.youtube.com/playlist?list={}'.format(m.group(1))
        if url:
            logger.info('youtube-dl handling %s => %s', channel.url, url)
            return self.refresh(url, channel.url, max_episodes)
        return None

    def is_supported_url(self, url):
        if url is None:
            return False
        for i, res in enumerate(self.regex_cache):
            if next(filter(None, (r.match(url) for r in res)), None) is not None:
                if i > 0:
                    self.regex_cache.remove(res)
                    self.regex_cache.insert(0, res)
                return True
        with youtube_dl.YoutubeDL(self._ydl_opts) as ydl:
            # youtube-dl returns a list, yt-dlp returns a dict
            ies = ydl._ies
            if isinstance(ydl._ies, dict):
                ies = ydl._ies.values()
            for ie in ies:
                if ie.suitable(url) and ie.ie_key() not in self.ie_blacklist:
                    self.regex_cache.insert(
                        0, (ie._VALID_URL_RE if isinstance(ie._VALID_URL_RE, Iterable)
                            else (ie._VALID_URL_RE,)))
                    return True
        return False

    def custom_downloader(self, unused_config, episode):
        """
        called from registry.custom_downloader.resolve
        """
        if not self.force and not self.my_config.manage_downloads:
            return None

        try:  # Reject URLs linking to known media files
            (_, ext) = util.filename_from_url(episode.url)
            if util.file_type_by_extension(ext) is not None:
                return None
        except Exception:
            pass

        if self.is_supported_url(episode.url):
            return YoutubeCustomDownload(self, episode.url, episode)

        return None


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.ytdl = None
        self.infobar = None

    def on_load(self):
        self.ytdl = gPodderYoutubeDL(self.container.manager.core.config, self.container.config)
        logger.info('Registering youtube-dl. (using %s %s)' % (program_name, youtube_dl.version.__version__))
        registry.feed_handler.register(self.ytdl.fetch_channel)
        registry.custom_downloader.register(self.ytdl.custom_downloader)

        if youtube_dl.utils.version_tuple(youtube_dl.version.__version__) < youtube_dl.utils.version_tuple(want_ytdl_version):
            logger.error(want_ytdl_version_msg
                % {'have_version': youtube_dl.version.__version__, 'want_version': want_ytdl_version})

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
        self.ytdl = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

            if youtube_dl.utils.version_tuple(youtube_dl.version.__version__) < youtube_dl.utils.version_tuple(want_ytdl_version):
                ui_object.notification(want_ytdl_version_msg %
                    {'have_version': youtube_dl.version.__version__, 'want_version': want_ytdl_version},
                    _('Old youtube-dl'), important=True, widget=ui_object.main_window)

    def on_episodes_context_menu(self, episodes):
        if not self.container.config.manage_downloads and any(e.can_download() for e in episodes):
            return [(_("Download with youtube-dl"), self.download_episodes)]

    def download_episodes(self, episodes):
        episodes = [e for e in episodes if e.can_download()]

        # create a new gPodderYoutubeDL to force using it even if manage_downloads is False
        downloader = gPodderYoutubeDL(self.container.manager.core.config, self.container.config, force=True)
        self.gpodder.download_episode_list(episodes, downloader=downloader)

    def toggle_manage_channel(self, widget):
        self.container.config.manage_channel = widget.get_active()

    def toggle_manage_downloads(self, widget):
        self.container.config.manage_downloads = widget.get_active()

    def toggle_embed_subtitles(self, widget):
        if widget.get_active():
            if not util.find_command('ffmpeg'):
                self.infobar.show()
                widget.set_active(False)
                self.container.config.embed_subtitles = False
            else:
                self.container.config.embed_subtitles = True
        else:
            self.container.config.embed_subtitles = False

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        label = Gtk.Label('%s %s' % (program_name, youtube_dl.version.__version__))
        box.pack_start(label, False, False, 0)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        checkbox = Gtk.CheckButton(_('Parse YouTube channel feeds with youtube-dl to access more than 15 episodes'))
        checkbox.set_active(self.container.config.manage_channel)
        checkbox.connect('toggled', self.toggle_manage_channel)
        box.pack_start(checkbox, False, False, 0)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        checkbox = Gtk.CheckButton(_('Download all supported episodes with youtube-dl'))
        checkbox.set_active(self.container.config.manage_downloads)
        checkbox.connect('toggled', self.toggle_manage_downloads)
        box.pack_start(checkbox, False, False, 0)
        note = Gtk.Label(use_markup=True, wrap=True, label=_(
            'youtube-dl provides access to additional YouTube formats and DRM content.'
            '  Episodes from non-YouTube channels, that have youtube-dl support, will <b>fail</b> to download unless you manually'
            ' <a href="https://gpodder.github.io/docs/youtube.html#formats">add custom formats</a> for each site.'
            '  <b>Download with youtube-dl</b> appears in the episode menu when this option is disabled,'
            ' and can be used to manually download from supported sites.'))
        note.connect('activate-link', lambda label, url: util.open_website(url))
        note.set_property('xalign', 0.0)
        box.add(note)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        checkbox = Gtk.CheckButton(_('Embed all available subtitles in downloaded video'))
        checkbox.set_active(self.container.config.embed_subtitles)
        checkbox.connect('toggled', self.toggle_embed_subtitles)
        box.pack_start(checkbox, False, False, 0)

        infobar = Gtk.InfoBar()
        infobar.get_content_area().add(Gtk.Label(wrap=True, label=_(
            'The "ffmpeg" command was not found. FFmpeg is required for embedding subtitles.')))
        self.infobar = infobar
        box.pack_end(infobar, False, False, 0)

        box.show_all()
        infobar.hide()
        return box

    def on_preferences(self):
        return [(_('youtube-dl'), self.show_preferences)]
