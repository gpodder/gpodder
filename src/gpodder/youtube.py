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
#  gpodder.youtube - YouTube and related magic
#  Justin Forest <justin.forest@gmail.com> 2008-10-13
#

import io
import json
import logging
import re
import urllib
import xml.etree.ElementTree
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import parse_qs

import gpodder
from gpodder import registry, util

logger = logging.getLogger(__name__)


_ = gpodder.gettext


# http://en.wikipedia.org/wiki/YouTube#Quality_and_formats
# https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L447

# adaptive audio formats
#   140  MP4   128k
#   251  WebM  160k
#   250  WebM  70k
#   249  WebM  50k

# formats and fallbacks of same quality: WebM -> MP4 -> FLV
flv_240 = [5]
flv_270 = [6]
flv_360 = [34]
flv_480 = [35]
mp4_144 = ['160+140']
mp4_240 = ['133+140'] + flv_240
mp4_360 = [18, '134+140'] + flv_360
mp4_480 = ['135+140'] + flv_480
mp4_720 = [22, '136+140']
mp4_1080 = [37, '137+140']
mp4_1440 = ['264+140']
mp4_2160 = ['266+140']
mp4_3072 = [38]
mp4_4320 = ['138+140']
webm_144 = ['278+250'] + mp4_144
webm_240 = ['242+250'] + mp4_240
webm_360 = [43, '243+251'] + mp4_360
webm_480 = [44, '244+251'] + mp4_480
webm_720 = [45, '247+251'] + mp4_720
webm_1080 = [46, '248+251'] + mp4_1080
webm_1440 = ['271+251'] + mp4_1440
webm_2160 = ['313+251'] + mp4_2160
webm_4320 = ['272+251'] + mp4_4320
# fallbacks to lower quality
webm_240 += webm_144
webm_360 += flv_270 + webm_240
webm_480 += webm_360
webm_720 += webm_480
webm_1080 += webm_720
webm_1440 += webm_1080
webm_2160 += webm_1440
webm_4320 += mp4_3072 + webm_2160
mp4_240 += mp4_144
mp4_360 += flv_270 + mp4_240
mp4_480 += mp4_360
mp4_720 += mp4_480
mp4_1080 += mp4_720
mp4_1440 += mp4_1080
mp4_2160 += mp4_1440
mp4_3072 += mp4_2160
mp4_4320 += mp4_3072
flv_270 += flv_240
flv_360 += flv_270
flv_480 += flv_360
# format id, (preferred ids, path(?), description) # video bitrate, audio bitrate
formats = [
    # WebM VP8, VP9 or VP9 HFR video, Vorbis or Opus audio
    # Fallback to MP4 or FLV
    (272, (webm_4320, '272/7680x4320/99/0/0', 'WebM 4320p 8K (7680x4320) youtube-dl')),  # N/A,      160 kbps
    (313, (webm_2160, '313/3840x2160/99/0/0', 'WebM 2160p 4K (3840x2160) youtube-dl')),  # N/A,      160 kbps
    (271, (webm_1440, '271/2560x1440/99/0/0', 'WebM 1440p (2560x1440) youtube-dl')),     # N/A,      160 kbps
    (46, (webm_1080, '46/1920x1080/99/0/0', 'WebM 1080p (1920x1080) youtube-dl')),       # N/A,      192 kbps
    (45, (webm_720, '45/1280x720/99/0/0', 'WebM 720p (1280x720) youtube-dl')),           # 2.0 Mbps, 192 kbps
    (44, (webm_480, '44/854x480/99/0/0', 'WebM 480p (854x480) youtube-dl')),             # 1.0 Mbps, 128 kbps
    (43, (webm_360, '43/640x360/99/0/0', 'WebM 360p (640x360)')),                        # 0.5 Mbps, 128 kbps
    (242, (webm_240, '242/426x240/99/0/0', 'WebM 240p (426x240) youtube-dl')),           # N/A,       70 kbps
    (278, (webm_144, '278/256x144/99/0/0', 'WebM 144p (256x144) youtube-dl')),           # N/A,       70 kbps

    # MP4 H.264 video, AAC audio
    # Fallback to FLV
    (138, (mp4_4320, '138/7680x4320/9/0/115', 'MP4 4320p 8K (7680x4320) youtube-dl')),  # N/A,       128 kbps
    (38, (mp4_3072, '38/4096x3072/9/0/115', 'MP4 3072p 4K (4096x3072)')),               # 5.0 - 3.5 Mbps, 192 kbps
    (266, (mp4_2160, '266/3840x2160/9/0/115', 'MP4 2160p 4K (3840x2160) youtube-dl')),  # N/A,       128 kbps
    (264, (mp4_1440, '264/2560x1440/9/0/115', 'MP4 1440p (2560x1440) youtube-dl')),     # N/A,       128 kbps
    (37, (mp4_1080, '37/1920x1080/9/0/115', 'MP4 1080p (1920x1080) youtube-dl')),       # 4.3 - 3.0 Mbps, 192 kbps
    (22, (mp4_720, '22/1280x720/9/0/115', 'MP4 720p (1280x720)')),                      # 2.9 - 2.0 Mbps, 192 kbps
    (135, (mp4_480, '135/854x480/9/0/115', 'MP4 480p (854x480) youtube-dl')),           # N/A,       128 kbps
    (18, (mp4_360, '18/640x360/9/0/115', 'MP4 360p (640x360)')),                        # 0.5 Mbps,   96 kbps
    (133, (mp4_240, '133/426x240/9/0/115', 'MP4 240p (426x240) youtube-dl')),           # N/A,       128 kbps
    (160, (mp4_144, '160/256x144/9/0/115', 'MP4 144p (256x144) youtube-dl')),           # N/A,       128 kbps

    # FLV H.264 video, AAC audio
    # Fallback to FLV 6 or 5
    (35, (flv_480, '35/854x480/9/0/115', 'FLV 480p (854x480)')),  # 1 - 0.80 Mbps, 128 kbps
    (34, (flv_360, '34/640x360/9/0/115', 'FLV 360p (640x360)')),  # 0.50 Mbps, 128 kbps

    # FLV Sorenson H.263 video, MP3 audio
    (6, (flv_270, '6/480x270/7/0/0', 'FLV 270p (480x270)')),  # 0.80 Mbps,  64 kbps
    (5, (flv_240, '5/320x240/7/0/0', 'FLV 240p (320x240)')),  # 0.25 Mbps,  64 kbps
]
formats_dict = dict(formats)

# streaming formats and fallbacks to lower quality
hls_144 = [91]
hls_240 = [92] + hls_144
hls_360 = [93] + hls_240
hls_480 = [94] + hls_360
hls_720 = [95] + hls_480
hls_1080 = [96] + hls_720
hls_formats = [
    (96, (hls_1080, '9/1920x1080/9/0/115', 'MP4 1080p (1920x1080)')),   # N/A,       256 kbps
    (95, (hls_720, '9/1280x720/9/0/115', 'MP4 720p (1280x720)')),       # N/A,       256 kbps
    (94, (hls_480, '9/854x480/9/0/115', 'MP4 480p (854x480)')),         # N/A,       128 kbps
    (93, (hls_360, '9/640x360/9/0/115', 'MP4 360p (640x360)')),         # N/A,       128 kbps
    (92, (hls_240, '9/426x240/9/0/115', 'MP4 240p (426x240)')),         # N/A,        48 kbps
    (91, (hls_144, '9/256x144/9/0/115', 'MP4 144p (256x144)')),         # N/A,        48 kbps
]
hls_formats_dict = dict(hls_formats)

CHANNEL_VIDEOS_XML = 'https://www.youtube.com/feeds/videos.xml'
WATCH_ENDPOINT = 'https://www.youtube.com/watch?bpctr=9999999999&has_verified=1&v='

# The page may contain "};" sequences inside the initial player response.
# Use a greedy match with script end tag, and fallback to a non-greedy match without.
INITIAL_PLAYER_RESPONSE_RE1 = r'ytInitialPlayerResponse\s*=\s*({.+})\s*;\s*</script'
INITIAL_PLAYER_RESPONSE_RE2 = r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;'


def get_ipr(page):
    for regex in (INITIAL_PLAYER_RESPONSE_RE1, INITIAL_PLAYER_RESPONSE_RE2):
        ipr = re.search(regex, page)
        if ipr is not None:
            return ipr
    return None


class YouTubeError(Exception):
    pass


def get_fmt_ids(youtube_config, allow_partial):
    if allow_partial:
        if youtube_config.preferred_hls_fmt_id == 0:
            hls_fmt_ids = (youtube_config.preferred_hls_fmt_ids if youtube_config.preferred_hls_fmt_ids else [])
        else:
            format = hls_formats_dict.get(youtube_config.preferred_hls_fmt_id)
            if format is None:
                hls_fmt_ids = []
            else:
                hls_fmt_ids, path, description = format
    else:
        hls_fmt_ids = []

    if youtube_config.preferred_fmt_id == 0:
        return (youtube_config.preferred_fmt_ids + hls_fmt_ids if youtube_config.preferred_fmt_ids else hls_fmt_ids)

    format = formats_dict.get(youtube_config.preferred_fmt_id)
    if format is None:
        return hls_fmt_ids
    fmt_ids, path, description = format
    return fmt_ids + hls_fmt_ids


@registry.download_url.register
def youtube_real_download_url(config, episode, allow_partial):
    fmt_ids = get_fmt_ids(config.youtube, allow_partial) if config else None
    res, duration = get_real_download_url(episode.url, allow_partial, fmt_ids)
    if duration is not None:
        episode.total_time = int(int(duration) / 1000)
    return None if res == episode.url else res


def youtube_get_old_endpoint(vid):
    # TODO: changing 'detailpage' to 'embedded' allows age-restricted content
    url = 'https://www.youtube.com/get_video_info?html5=1&c=TVHTML5&cver=6.20180913&el=detailpage&video_id=' + vid
    r = util.urlopen(url)
    if not r.ok:
        raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))
    else:
        return r.text, None


def youtube_get_new_endpoint(vid):
    url = WATCH_ENDPOINT + vid
    r = util.urlopen(url)
    if not r.ok:
        raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))

    ipr = get_ipr(r.text)
    if ipr is None:
        try:
            url = get_gdpr_consent_url(r.text)
        except YouTubeError as e:
            raise YouTubeError('Youtube "%s": No ytInitialPlayerResponse found and %s' % (url, str(e)))
        r = util.urlopen(url)
        if not r.ok:
            raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))

        ipr = get_ipr(r.text)
        if ipr is None:
            raise YouTubeError('Youtube "%s": No ytInitialPlayerResponse found' % url)

    return None, ipr.group(1)


def get_total_time(episode):
    try:
        vid = get_youtube_id(episode.url)
        if vid is None:
            return 0

        url = WATCH_ENDPOINT + vid
        r = util.urlopen(url)
        if not r.ok:
            return 0

        ipr = get_ipr(r.text)
        if ipr is None:
            url = get_gdpr_consent_url(r.text)
            r = util.urlopen(url)
            if not r.ok:
                return 0

            ipr = get_ipr(r.text)
            if ipr is None:
                return 0

        player_response = json.loads(ipr.group(1))
        return int(player_response['videoDetails']['lengthSeconds'])  # 0 if live
    except:
        return 0


def get_real_download_url(url, allow_partial, preferred_fmt_ids=None):
    if not preferred_fmt_ids:
        preferred_fmt_ids, _, _ = formats_dict[22]  # MP4 720p

    duration = None

    vid = get_youtube_id(url)
    if vid is not None:
        try:
            old_page, new_page = youtube_get_new_endpoint(vid)
        except YouTubeError as e:
            logger.info(str(e))
            old_page, new_page = youtube_get_old_endpoint(vid)

        def find_urls(old_page, new_page):
            # streamingData is preferable to url_encoded_fmt_stream_map
            # streamingData.formats are the same as url_encoded_fmt_stream_map
            # streamingData.adaptiveFormats are audio-only and video-only formats

            x = parse_qs(old_page) if old_page else json.loads(new_page)
            player_response = json.loads(x['player_response'][0]) if old_page and 'player_response' in x else x
            error_message = None

            if 'reason' in x:
                # TODO: unknown if this is valid for new_page
                error_message = util.remove_html_tags(x['reason'][0])
            elif 'playabilityStatus' in player_response:
                playabilityStatus = player_response['playabilityStatus']

                if 'reason' in playabilityStatus:
                    error_message = util.remove_html_tags(playabilityStatus['reason'])
                elif 'liveStreamability' in playabilityStatus \
                        and not playabilityStatus['liveStreamability'].get('liveStreamabilityRenderer', {}).get('displayEndscreen', False):
                    # playabilityStatus.liveStreamability -- video is or was a live stream
                    # playabilityStatus.liveStreamability.liveStreamabilityRenderer.displayEndscreen -- video has ended if present

                    if allow_partial and 'streamingData' in player_response and 'hlsManifestUrl' in player_response['streamingData']:
                        r = util.urlopen(player_response['streamingData']['hlsManifestUrl'])
                        if not r.ok:
                            raise YouTubeError('HLS Manifest: %d %s' % (r.status_code, r.reason))
                        manifest = r.text.splitlines()

                        urls = [line for line in manifest if line[0] != '#']
                        itag_re = re.compile(r'/itag/([0-9]+)/')
                        for url in urls:
                            itag = itag_re.search(url).group(1)
                            yield int(itag), [url, None]
                        return

                    error_message = 'live stream'
                elif 'streamingData' in player_response:
                    if 'formats' in player_response['streamingData']:
                        for f in player_response['streamingData']['formats']:
                            if 'url' in f:  # DRM videos store url inside a signatureCipher key
                                yield int(f['itag']), [f['url'], f.get('approxDurationMs')]
                    if 'adaptiveFormats' in player_response['streamingData']:
                        for f in player_response['streamingData']['adaptiveFormats']:
                            if 'url' in f:  # DRM videos store url inside a signatureCipher key
                                yield int(f['itag']), [f['url'], f.get('approxDurationMs')]
                    return

            if error_message is not None:
                raise YouTubeError(('Cannot stream video: %s' if allow_partial else 'Cannot download video: %s') % error_message)

            if old_page:
                r4 = re.search(r'url_encoded_fmt_stream_map=([^&]+)', old_page)
                if r4 is not None:
                    fmt_url_map = urllib.parse.unquote(r4.group(1))
                    for fmt_url_encoded in fmt_url_map.split(','):
                        video_info = parse_qs(fmt_url_encoded)
                        yield int(video_info['itag'][0]), [video_info['url'][0], None]

        fmt_id_url_map = sorted(find_urls(old_page, new_page), reverse=True)

        if not fmt_id_url_map:
            drm = re.search(r'(%22(cipher|signatureCipher)%22%3A|"signatureCipher":)', old_page or new_page)
            if drm is not None:
                raise YouTubeError('Unsupported DRM content')
            raise YouTubeError('No formats found')

        formats_available = set(fmt_id for fmt_id, url in fmt_id_url_map)
        fmt_id_url_map = dict(fmt_id_url_map)

        for id in preferred_fmt_ids:
            if not re.search(r'^[0-9]+$', str(id)):
                # skip non-integer formats 'best', '136+140' or twitch '720p'
                continue
            id = int(id)
            if id in formats_available:
                format = formats_dict.get(id) or hls_formats_dict.get(id)
                if format is not None:
                    _, _, description = format
                else:
                    description = 'Unknown'

                logger.info('Found YouTube format: %s (fmt_id=%d)',
                        description, id)
                url, duration = fmt_id_url_map[id]
                break
        else:
            raise YouTubeError('No preferred formats found')

    return url, duration


@lru_cache(1)
def get_youtube_id(url):
    r = re.compile(r'http[s]?://(?:[a-z]+\.)?youtube\.com/watch\?v=([^&]*)', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile(r'http[s]?://(?:[a-z]+\.)?youtube\.com/v/(.*)[?]', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile(r'http[s]?://(?:[a-z]+\.)?youtube\.com/v/(.*)\.swf', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    return for_each_feed_pattern(lambda url, channel: channel, url, None)


def is_video_link(url):
    return (get_youtube_id(url) is not None)


def is_youtube_guid(guid):
    return guid.startswith('tag:youtube.com,2008:video:')


def for_each_feed_pattern(func, url, fallback_result):
    """
    Try to find the username for all possible YouTube feed/webpage URLs
    Will call func(url, channel) for each match, and if func() returns
    a result other than None, returns this. If no match is found or
    func() returns None, return fallback_result.
    """
    CHANNEL_MATCH_PATTERNS = [
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/user/([a-z0-9]+)',
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/profile?user=([a-z0-9]+)',
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/rss/user/([a-z0-9]+)/videos\.rss',
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/channel/([-_a-z0-9]+)',
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/feeds/videos.xml\?user=([a-z0-9]+)',
        r'http[s]?://(?:[a-z]+\.)?youtube\.com/feeds/videos.xml\?channel_id=([-_a-z0-9]+)',
        r'http[s]?://gdata.youtube.com/feeds/users/([^/]+)/uploads',
        r'http[s]?://gdata.youtube.com/feeds/base/users/([^/]+)/uploads',
    ]

    for pattern in CHANNEL_MATCH_PATTERNS:
        m = re.match(pattern, url, re.IGNORECASE)
        if m is not None:
            result = func(url, m.group(1))
            if result is not None:
                return result

    return fallback_result


def get_real_channel_url(url):
    def return_user_feed(url, channel):
        result = 'https://gdata.youtube.com/feeds/users/{0}/uploads'.format(channel)
        logger.debug('YouTube link resolved: %s => %s', url, result)
        return result

    return for_each_feed_pattern(return_user_feed, url, url)


@lru_cache(1)
def get_channel_id_url(url, feed_data=None):
    if 'youtube.com' in url:
        try:
            if feed_data is None:
                r = util.urlopen(url)
                if not r.ok:
                    raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))
            else:
                r = feed_data
            # video page may contain corrupt HTML/XML, search for tag to avoid exception
            m = re.search(r'channel_id=([^"]+)">', r.text)
            if m:
                channel_id = m.group(1)
            else:
                raw_xml_data = io.BytesIO(r.content)
                xml_data = xml.etree.ElementTree.parse(raw_xml_data)
                channel_id = xml_data.find("{http://www.youtube.com/xml/schemas/2015}channelId").text
                if channel_id is None:
                    # check entries if feed has an empty channelId
                    m = re.search(r'<yt:channelId>([^<]+)</yt:channelId>', r.text)
                    if m:
                        channel_id = m.group(1)
                    if channel_id is None:
                        raise Exception('Could not retrieve YouTube channel ID for URL %s.' % url)
            channel_url = 'https://www.youtube.com/channel/{}'.format(channel_id)
            return channel_url

        except Exception:
            logger.warning('Could not retrieve YouTube channel ID for URL %s.' % url, exc_info=True)

    raise Exception('Could not retrieve YouTube channel ID for URL %s.' % url)


def get_cover(url, feed_data=None):
    if 'youtube.com' in url:

        class YouTubeHTMLCoverParser(HTMLParser):
            """This custom html parser searches for the youtube channel thumbnail/avatar"""
            def __init__(self):
                super().__init__()
                self.url = []

            def handle_starttag(self, tag, attributes):
                attribute_dict = {attribute[0]: attribute[1] for attribute in attributes}

                # Look for 900x900px image first.
                if tag == 'link' \
                        and 'rel' in attribute_dict \
                        and attribute_dict['rel'] == 'image_src':
                    self.url.append(attribute_dict['href'])

                # Fallback to image that may only be 100x100px.
                elif tag == 'img' \
                        and 'class' in attribute_dict \
                        and attribute_dict['class'] == "channel-header-profile-image":
                    self.url.append(attribute_dict['src'])

        try:
            channel_url = get_channel_id_url(url, feed_data)
            r = util.urlopen(channel_url)
            if not r.ok:
                raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))
            html_data = util.response_text(r)
            parser = YouTubeHTMLCoverParser()
            parser.feed(html_data)
            if parser.url:
                logger.debug('Youtube cover art for {} is: {}'.format(url, parser.url))
                return parser.url[0]

        except Exception:
            logger.warning('Could not retrieve cover art', exc_info=True)


def get_gdpr_consent_url(html_data):
    """
    Creates the URL for automatically accepting GDPR consents
    EU GDPR redirects to a form that needs to be posted to be redirected to a get request
    with the form data as input to the youtube video URL. This extracts that form data from
    the GDPR form and builds up the URL the posted form results.
    """
    class ConsentHTML(HTMLParser):
        def __init__(self):
            super().__init__()
            self.url = ''
            self.consentForm = False

        def handle_starttag(self, tag, attributes):
            attribute_dict = {attribute[0]: attribute[1] for attribute in attributes}
            if tag == 'form' and attribute_dict['action'] == 'https://consent.youtube.com/s':
                self.consentForm = True
                self.url = 'https://consent.google.com/s?'
            # Get GDPR form elements
            if self.consentForm and tag == 'input' and attribute_dict['type'] == 'hidden':
                self.url += '&' + attribute_dict['name'] + '=' + urllib.parse.quote_plus(attribute_dict['value'])

        def handle_endtag(self, tag):
            if tag == 'form':
                self.consentForm = False

    try:
        parser = ConsentHTML()
        parser.feed(html_data)
    except Exception:
        raise YouTubeError('Could not retrieve GDPR accepted consent URL')

    if parser.url:
        logger.debug('YouTube GDPR accept consent URL is: %s', parser.url)
        return parser.url
    else:
        logger.debug('YouTube GDPR accepted consent URL could not be resolved.')
        raise YouTubeError('No acceptable GDPR consent URL')


def get_channel_desc(url, feed_data=None):
    if 'youtube.com' in url:

        class YouTubeHTMLDesc(HTMLParser):
            """This custom html parser searches for the YouTube channel description."""
            def __init__(self):
                super().__init__()
                self.description = ''

            def handle_starttag(self, tag, attributes):
                attribute_dict = {attribute[0]: attribute[1] for attribute in attributes}

                # Get YouTube channel description.
                if tag == 'meta' \
                        and 'name' in attribute_dict \
                        and attribute_dict['name'] == "description":
                    self.description = attribute_dict['content']

        try:
            channel_url = get_channel_id_url(url, feed_data)
            r = util.urlopen(channel_url)
            if not r.ok:
                raise YouTubeError('Youtube "%s": %d %s' % (url, r.status_code, r.reason))
            html_data = util.response_text(r)
            parser = YouTubeHTMLDesc()
            parser.feed(html_data)
            if parser.description:
                logger.debug('YouTube description for %s is: %s', url, parser.description)
                return parser.description
            else:
                logger.debug('YouTube description for %s is not provided.', url)
                return _('No description available')

        except Exception:
            logger.warning('Could not retrieve YouTube channel description for %s.' % url, exc_info=True)


def parse_youtube_url(url):
    """
    Youtube Channel Links are parsed into youtube feed links
    >>> parse_youtube_url("https://www.youtube.com/channel/CHANNEL_ID")
    'https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID'

    Youtube User Links are parsed into youtube feed links
    >>> parse_youtube_url("https://www.youtube.com/user/USERNAME")
    'https://www.youtube.com/feeds/videos.xml?user=USERNAME'

    Youtube Playlist Links are parsed into youtube feed links
    >>> parse_youtube_url("https://www.youtube.com/playlist?list=PLAYLIST_ID")
    'https://www.youtube.com/feeds/videos.xml?playlist_id=PLAYLIST_ID'

    >>> parse_youtube_url(None)
    None

    @param url: the path to the channel, user or playlist
    @return: the feed url if successful or the given url if not
    """
    if url is None:
        return url
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    logger.debug("Analyzing URL: {}".format(" ".join([scheme, netloc, path, query, fragment])))

    if 'youtube.com' in netloc:
        if path == '/feeds/videos.xml' and re.search(r'^(user|channel|playlist)_id=.*', query):
            return url

        if '/user/' in path or '/channel/' in path or 'list=' in query:
            logger.debug("Valid Youtube URL detected. Parsing...")

            if path.startswith('/user/'):
                user_id = path.split('/')[2]
                query = 'user={user_id}'.format(user_id=user_id)

            if path.startswith('/channel/'):
                channel_id = path.split('/')[2]
                query = 'channel_id={channel_id}'.format(channel_id=channel_id)

            if 'list=' in query:
                playlist_query = [query_value for query_value in query.split("&") if 'list=' in query_value][0]
                playlist_id = playlist_query[5:]
                query = 'playlist_id={playlist_id}'.format(playlist_id=playlist_id)

            path = '/feeds/videos.xml'

            new_url = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))
            logger.debug("New Youtube URL: {}".format(new_url))
            return new_url

        # look for channel URL in page
        new_url = get_channel_id_url(url)
        if new_url:
            logger.debug("New Youtube URL: {}".format(new_url))
            return new_url

    logger.debug("Not a valid Youtube URL: {}".format(url))
    return url
