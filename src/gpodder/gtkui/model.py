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


#
#  gpodder.gtkui.model - GUI model classes for gPodder (2009-08-13)
#  Based on code from libpodcasts.py (thp, 2005-10-29)
#

import html
import logging
import os
import re
import time
from itertools import groupby

from gi.repository import GdkPixbuf, GLib, GObject, Gtk

import gpodder
from gpodder import coverart, model, query, util
from gpodder.gtkui import draw

_ = gpodder.gettext

logger = logging.getLogger(__name__)


try:
    from gi.repository import Gio
    have_gio = True
except ImportError:
    have_gio = False

# ----------------------------------------------------------


class GEpisode(model.PodcastEpisode):
    __slots__ = ()

    @property
    def title_markup(self):
        return '%s\n<small>%s</small>' % (html.escape(self.title),
                          html.escape(self.channel.title))

    @property
    def markup_new_episodes(self):
        if self.file_size > 0:
            length_str = '%s; ' % util.format_filesize(self.file_size)
        else:
            length_str = ''
        return ('<b>%s</b>\n<small>%s' + _('released %s')
                + '; ' + _('from %s') + '</small>') % (
                html.escape(re.sub(r'\s+', ' ', self.title)),
                html.escape(length_str),
                html.escape(self.pubdate_prop),
                html.escape(re.sub(r'\s+', ' ', self.channel.title)))

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
        return ('<b>%s</b>\n<small>%s; %s; ' + _('downloaded %s')
                + '; ' + _('from %s') + '</small>') % (
                html.escape(self.title),
                html.escape(util.format_filesize(self.file_size)),
                html.escape(played_string),
                html.escape(downloaded_string),
                html.escape(self.channel.title))


class GPodcast(model.PodcastChannel):
    __slots__ = ()

    EpisodeClass = GEpisode

    @property
    def title_markup(self):
        """ escaped title for the mass unsubscribe dialog """
        return html.escape(self.title)


class Model(model.Model):
    PodcastClass = GPodcast

# ----------------------------------------------------------


# Singleton indicator if a row is a section
class SeparatorMarker(object): pass


class BackgroundUpdate(object):
    def __init__(self, model, episodes):
        self.model = model
        self.episodes = episodes
        self.index = 0

    def update(self):
        model = self.model

        started = time.time()
        while self.episodes:
            episode = self.episodes.pop(0)
            base_fields = (
                model.C_URL, episode.url,
                model.C_TITLE, episode.title,
                model.C_EPISODE, episode,
                model.C_PUBLISHED_TEXT, episode.cute_pubdate(show_time=self.model._config_ui_gtk_episode_list_show_released_time),
                model.C_PUBLISHED, episode.published,
            )
            update_fields = model.get_update_fields(episode)
            try:
                it = model.get_iter((self.index,))
            # fix #727 the tree might be invalid when trying to update so discard the exception
            except ValueError:
                break
            # model.get_update_fields() takes 38-67% of each iteration, depending on episode status
            # with downloaded episodes using the most time
            # model.set(), excluding the field expansion, takes 33-62% of each iteration
            # and each iteration takes 1ms or more on slow machines
            model.set(it, *(base_fields + update_fields))
            self.index += 1

            # Check for the time limit of 500ms after each 50 rows processed
            if self.index % 50 == 0 and (time.time() - started) > 0.5:
                break

        return bool(self.episodes)


class EpisodeListModel(Gtk.ListStore):
    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
        C_PUBLISHED_TEXT, C_DESCRIPTION, C_TOOLTIP, \
        C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
        C_VIEW_SHOW_UNPLAYED, C_FILESIZE, C_PUBLISHED, \
        C_TIME, C_TIME_VISIBLE, C_TOTAL_TIME, \
        C_LOCKED, \
        C_TIME_AND_SIZE, C_TOTAL_TIME_AND_SIZE, C_FILESIZE_AND_TIME_TEXT, C_FILESIZE_AND_TIME = list(range(21))

    VIEW_ALL, VIEW_UNDELETED, VIEW_DOWNLOADED, VIEW_UNPLAYED = list(range(4))

    VIEWS = ['VIEW_ALL', 'VIEW_UNDELETED', 'VIEW_DOWNLOADED', 'VIEW_UNPLAYED']

    # In which steps the UI is updated for "loading" animations
    _UI_UPDATE_STEP = .03

    # Steps for the "downloading" icon progress
    PROGRESS_STEPS = 20

    def __init__(self, on_filter_changed=lambda has_episodes: None):
        Gtk.ListStore.__init__(self, str, str, str, object, str, str, str,
                               str, bool, bool, bool, GObject.TYPE_INT64,
                               GObject.TYPE_INT64, str, bool,
                               GObject.TYPE_INT64, bool, str, GObject.TYPE_INT64, str, GObject.TYPE_INT64)

        # Callback for when the filter / list changes, gets one parameter
        # (has_episodes) that is True if the list has any episodes
        self._on_filter_changed = on_filter_changed

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._sorter = Gtk.TreeModelSort(self._filter)
        self._view_mode = self.VIEW_ALL
        self._search_term = None
        self._search_term_eql = None
        self._filter.set_visible_func(self._filter_visible_func)

        # Are we currently showing "all episodes"/section or a single channel?
        self._section_view = False

        self.icon_theme = Gtk.IconTheme.get_default()
        self.ICON_WEB_BROWSER = 'web-browser'
        self.ICON_AUDIO_FILE = 'audio-x-generic'
        self.ICON_VIDEO_FILE = 'video-x-generic'
        self.ICON_IMAGE_FILE = 'image-x-generic'
        self.ICON_GENERIC_FILE = 'text-x-generic'
        self.ICON_DOWNLOADING = 'go-down'
        self.ICON_DELETED = 'edit-delete'
        self.ICON_ERROR = 'dialog-error'

        self.background_update = None
        self.background_update_tag = None

        if 'KDE_FULL_SESSION' in os.environ:
            # Workaround until KDE adds all the freedesktop icons
            # See https://bugs.kde.org/show_bug.cgi?id=233505 and
            #     http://gpodder.org/bug/553
            self.ICON_DELETED = 'archive-remove'

        # Caching config values is faster than accessing them directly from config.ui.gtk.episode_list.*
        # and is easier to maintain then threading them through every method call.
        self._config_ui_gtk_episode_list_always_show_new = False
        self._config_ui_gtk_episode_list_trim_title_prefix = False
        self._config_ui_gtk_episode_list_descriptions = False
        self._config_ui_gtk_episode_list_show_released_time = False

    def cache_config(self, config):
        self._config_ui_gtk_episode_list_always_show_new = config.ui.gtk.episode_list.always_show_new
        self._config_ui_gtk_episode_list_trim_title_prefix = config.ui.gtk.episode_list.trim_title_prefix
        self._config_ui_gtk_episode_list_descriptions = config.ui.gtk.episode_list.descriptions
        self._config_ui_gtk_episode_list_show_released_time = config.ui.gtk.episode_list.show_released_time

    def _format_filesize(self, episode):
        if episode.file_size > 0:
            return util.format_filesize(episode.file_size, digits=1)
        else:
            return None

    def _filter_visible_func(self, model, iter, misc):
        # If searching is active, set visibility based on search text
        if self._search_term is not None and self._search_term != '':
            episode = model.get_value(iter, self.C_EPISODE)
            if episode is None:
                return False

            try:
                return self._search_term_eql.match(episode)
            except Exception as e:
                return True

        if self._view_mode == self.VIEW_ALL:
            return True
        elif self._view_mode == self.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNDELETED)
        elif self._view_mode == self.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VIEW_SHOW_DOWNLOADED)
        elif self._view_mode == self.VIEW_UNPLAYED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNPLAYED)

        return True

    def get_filtered_model(self):
        """Returns a filtered version of this episode model

        The filtered version should be displayed in the UI,
        as this model can have some filters set that should
        be reflected in the UI.
        """
        return self._sorter

    def has_episodes(self):
        """Returns True if episodes are visible (filtered)

        If episodes are visible with the current filter
        applied, return True (otherwise return False).
        """
        return bool(len(self._filter))

    def set_view_mode(self, new_mode):
        """Sets a new view mode for this model

        After setting the view mode, the filtered model
        might be updated to reflect the new mode."""
        if self._view_mode != new_mode:
            self._view_mode = new_mode
            self._filter.refilter()
            self._on_filter_changed(self.has_episodes())

    def get_view_mode(self):
        """Returns the currently-set view mode"""
        return self._view_mode

    def set_search_term(self, new_term):
        if self._search_term != new_term:
            self._search_term = new_term
            self._search_term_eql = query.UserEQL(new_term)
            self._filter.refilter()
            self._on_filter_changed(self.has_episodes())

    def get_search_term(self):
        return self._search_term

    def _format_description(self, episode):
        d = []

        title = episode.trimmed_title if self._config_ui_gtk_episode_list_trim_title_prefix else episode.title
        if episode.state != gpodder.STATE_DELETED and episode.is_new:
            d.append('<b>')
            d.append(html.escape(title))
            d.append('</b>')
        else:
            d.append(html.escape(title))

        if self._config_ui_gtk_episode_list_descriptions:
            d.append('\n')
            if self._section_view:
                d.append(_('from %s') % html.escape(episode.channel.title))
            else:
                description = episode.one_line_description()
                if description.startswith(title):
                    description = description[len(title):].strip()
                d.append(html.escape(description))

        return ''.join(d)

    def replace_from_channel(self, channel):
        """
        Add episode from the given channel to this model.
        Downloading should be a callback.
        """

        # Remove old episodes in the list store
        self.clear()

        self._section_view = isinstance(channel, PodcastChannelProxy)

        # Avoid gPodder bug 1291
        if channel is None:
            episodes = []
        else:
            episodes = channel.get_all_episodes()

        # Always make a copy, so we can pass the episode list to BackgroundUpdate
        episodes = list(episodes)

        for _ in range(len(episodes)):
            self.append()

        self._update_from_episodes(episodes)

    def _update_from_episodes(self, episodes):
        if self.background_update_tag is not None:
            GLib.source_remove(self.background_update_tag)

        self.background_update = BackgroundUpdate(self, episodes)
        self.background_update_tag = GLib.idle_add(self._update_background)

    def _update_background(self):
        if self.background_update is not None:
            if self.background_update.update():
                return True

            self.background_update = None
            self.background_update_tag = None
            self._on_filter_changed(self.has_episodes())

        return False

    def update_all(self):
        if self.background_update is None:
            episodes = [row[self.C_EPISODE] for row in self]
        else:
            # Update all episodes that have already been initialized...
            episodes = [row[self.C_EPISODE] for index, row in enumerate(self) if index < self.background_update.index]
            # ...and also include episodes that still need to be initialized
            episodes.extend(self.background_update.episodes)

        self._update_from_episodes(episodes)

    def update_by_urls(self, urls):
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter)

    def update_by_filter_iter(self, iter):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
        iter = self._sorter.convert_iter_to_child_iter(iter)
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def get_update_fields(self, episode):
        tooltip = []
        status_icon = None
        view_show_undeleted = True
        view_show_downloaded = False
        view_show_unplayed = False

        if episode.downloading:
            task = episode.download_task
            if task.status in (task.PAUSING, task.PAUSED):
                tooltip.append('%s %d%%' % (_('Paused'),
                    int(task.progress * 100)))
                status_icon = 'media-playback-pause'
            else:
                tooltip.append('%s %d%%' % (_('Downloading'),
                    int(task.progress * 100)))
                index = int(self.PROGRESS_STEPS * task.progress)
                status_icon = 'gpodder-progress-%d' % index

            view_show_downloaded = True
            view_show_unplayed = True
        else:
            if episode.state == gpodder.STATE_DELETED:
                tooltip.append(_('Deleted'))
                status_icon = self.ICON_DELETED
                view_show_undeleted = False
            elif episode.state == gpodder.STATE_DOWNLOADED:
                view_show_downloaded = True
                view_show_unplayed = episode.is_new

                file_type = episode.file_type()
                if file_type == 'audio':
                    tooltip.append(_('Downloaded episode'))
                    status_icon = self.ICON_AUDIO_FILE
                elif file_type == 'video':
                    tooltip.append(_('Downloaded video episode'))
                    status_icon = self.ICON_VIDEO_FILE
                elif file_type == 'image':
                    tooltip.append(_('Downloaded image'))
                    status_icon = self.ICON_IMAGE_FILE
                else:
                    tooltip.append(_('Downloaded file'))
                    status_icon = self.ICON_GENERIC_FILE

                if not episode.file_exists():
                    tooltip.append(_('missing file'))
                else:
                    if episode.is_new:
                        if file_type in ('audio', 'video'):
                            tooltip.append(_('never played'))
                        elif file_type == 'image':
                            tooltip.append(_('never displayed'))
                        else:
                            tooltip.append(_('never opened'))
                    else:
                        if file_type in ('audio', 'video'):
                            tooltip.append(_('played'))
                        elif file_type == 'image':
                            tooltip.append(_('displayed'))
                        else:
                            tooltip.append(_('opened'))
                    if episode.archive:
                        tooltip.append(_('deletion prevented'))

                if episode.total_time > 0 and episode.current_position:
                    tooltip.append('%d%%' % (
                        100. * float(episode.current_position) / float(episode.total_time)))
            elif episode._download_error is not None:
                tooltip.append(_('ERROR: %s') % episode._download_error)
                status_icon = self.ICON_ERROR
                if episode.state == gpodder.STATE_NORMAL and episode.is_new:
                    view_show_downloaded = self._config_ui_gtk_episode_list_always_show_new
                    view_show_unplayed = True
            elif not episode.url:
                tooltip.append(_('No downloadable content'))
                status_icon = self.ICON_WEB_BROWSER
                if episode.state == gpodder.STATE_NORMAL and episode.is_new:
                    view_show_downloaded = self._config_ui_gtk_episode_list_always_show_new
                    view_show_unplayed = True
            elif episode.state == gpodder.STATE_NORMAL and episode.is_new:
                tooltip.append(_('New episode'))
                view_show_downloaded = self._config_ui_gtk_episode_list_always_show_new
                view_show_unplayed = True

        if episode.total_time:
            total_time = util.format_time(episode.total_time)
            if total_time:
                tooltip.append(total_time)

        tooltip = ', '.join(tooltip)

        description = self._format_description(episode)
        time = episode.get_play_info_string()
        filesize = self._format_filesize(episode)

        return (
                self.C_STATUS_ICON, status_icon,
                self.C_VIEW_SHOW_UNDELETED, view_show_undeleted,
                self.C_VIEW_SHOW_DOWNLOADED, view_show_downloaded,
                self.C_VIEW_SHOW_UNPLAYED, view_show_unplayed,
                self.C_DESCRIPTION, description,
                self.C_TOOLTIP, tooltip,
                self.C_TIME, time,
                self.C_TIME_VISIBLE, bool(episode.total_time),
                self.C_TOTAL_TIME, episode.total_time,
                self.C_LOCKED, episode.archive,
                self.C_FILESIZE_TEXT, filesize,
                self.C_FILESIZE, episode.file_size,

                self.C_TIME_AND_SIZE, "%s\n<small>%s</small>" % (time, filesize if episode.file_size > 0 else ""),
                self.C_TOTAL_TIME_AND_SIZE, episode.total_time,
                self.C_FILESIZE_AND_TIME_TEXT, "%s\n<small>%s</small>" % (filesize if episode.file_size > 0 else "", time),
                self.C_FILESIZE_AND_TIME, episode.file_size,
        )

    def update_by_iter(self, iter):
        episode = self.get_value(iter, self.C_EPISODE)
        if episode is not None:
            self.set(iter, *self.get_update_fields(episode))


class PodcastChannelProxy:
    """ a bag of podcasts: 'All Episodes' or each section """
    def __init__(self, db, config, channels, section, model):
        self.ALL_EPISODES_PROXY = not bool(section)
        self._db = db
        self._config = config
        self.channels = channels
        if self.ALL_EPISODES_PROXY:
            self.title = _('All episodes')
            self.description = _('from all podcasts')
            self.url = ''
            self.cover_file = coverart.CoverDownloader.ALL_EPISODES_ID
        else:
            self.title = section
            self.description = ''
            self.url = '-'
            self.cover_file = None
        # self.parse_error = ''
        self.section = section
        self.id = None
        self.cover_url = None
        self.auth_username = None
        self.auth_password = None
        self.pause_subscription = False
        self.sync_to_mp3_player = False
        self.cover_thumb = None
        self.auto_archive_episodes = False
        self.model = model

        self._update_error = None

    def get_statistics(self):
        if self.ALL_EPISODES_PROXY:
            # Get the total statistics for all channels from the database
            return self._db.get_podcast_statistics()
        else:
            # Calculate the stats over all podcasts of this section
            if len(self.channels) == 0:
                total = deleted = new = downloaded = unplayed = 0
            else:
                total, deleted, new, downloaded, unplayed = list(map(sum,
                        list(zip(*[c.get_statistics() for c in self.channels]))))
            return total, deleted, new, downloaded, unplayed

    def get_all_episodes(self):
        """Returns a generator that yields every episode"""
        if self.model._search_term is not None:
            def matches(channel):
                columns = (getattr(channel, c) for c in PodcastListModel.SEARCH_ATTRS)
                return any((key in c.lower() for c in columns if c is not None))
            key = self.model._search_term
        else:
            def matches(e):
                return True
        return Model.sort_episodes_by_pubdate((e for c in self.channels if matches(c)
            for e in c.get_all_episodes()), True)

    def save(self):
        pass


class PodcastListModel(Gtk.ListStore):
    C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL, \
        C_COVER, C_ERROR, C_PILL_VISIBLE, \
        C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
        C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR, \
        C_DOWNLOADS, C_COVER_VISIBLE, C_SECTION = list(range(16))

    SEARCH_COLUMNS = (C_TITLE, C_DESCRIPTION, C_SECTION)
    SEARCH_ATTRS = ('title', 'description', 'group_by')

    @classmethod
    def row_separator_func(cls, model, iter):
        return model.get_value(iter, cls.C_SEPARATOR)

    def __init__(self, cover_downloader):
        Gtk.ListStore.__init__(self, str, str, str, GdkPixbuf.Pixbuf,
                object, GdkPixbuf.Pixbuf, str, bool, bool, bool, bool,
                bool, bool, int, bool, str)

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = -1
        self._search_term = None
        self._filter.set_visible_func(self._filter_visible_func)

        self._cover_cache = {}
        self._max_image_side = 40
        self._scale = 1
        self._cover_downloader = cover_downloader

        self.icon_theme = Gtk.IconTheme.get_default()
        self.ICON_DISABLED = 'media-playback-pause'
        self.ICON_ERROR = 'dialog-warning'

    def _filter_visible_func(self, model, iter, misc):
        channel = model.get_value(iter, self.C_CHANNEL)

        # If searching is active, set visibility based on search text
        if self._search_term is not None and self._search_term != '':
            key = self._search_term.lower()
            if isinstance(channel, PodcastChannelProxy):
                if channel.ALL_EPISODES_PROXY:
                    return False
                return any(key in getattr(ch, c).lower() for c in PodcastListModel.SEARCH_ATTRS for ch in channel.channels)
            columns = (model.get_value(iter, c) for c in self.SEARCH_COLUMNS)
            return any((key in c.lower() for c in columns if c is not None))

        # Show section if any of its channels have an update error
        if isinstance(channel, PodcastChannelProxy) and not channel.ALL_EPISODES_PROXY:
            if any(c._update_error is not None for c in channel.channels):
                return True

        if model.get_value(iter, self.C_SEPARATOR):
            return True
        elif getattr(channel, '_update_error', None) is not None:
            return True
        elif self._view_mode == EpisodeListModel.VIEW_ALL:
            return model.get_value(iter, self.C_HAS_EPISODES)
        elif self._view_mode == EpisodeListModel.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNDELETED)
        elif self._view_mode == EpisodeListModel.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VIEW_SHOW_DOWNLOADED)
        elif self._view_mode == EpisodeListModel.VIEW_UNPLAYED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNPLAYED)

        return True

    def get_filtered_model(self):
        """Returns a filtered version of this episode model

        The filtered version should be displayed in the UI,
        as this model can have some filters set that should
        be reflected in the UI.
        """
        return self._filter

    def set_view_mode(self, new_mode):
        """Sets a new view mode for this model

        After setting the view mode, the filtered model
        might be updated to reflect the new mode."""
        if self._view_mode != new_mode:
            self._view_mode = new_mode
            self._filter.refilter()

    def get_view_mode(self):
        """Returns the currently-set view mode"""
        return self._view_mode

    def set_search_term(self, new_term):
        if self._search_term != new_term:
            self._search_term = new_term
            self._filter.refilter()

    def get_search_term(self):
        return self._search_term

    def set_max_image_size(self, size, scale):
        self._max_image_side = size * scale
        self._scale = scale
        self._cover_cache = {}

    def _resize_pixbuf_keep_ratio(self, url, pixbuf):
        """
        Resizes a GTK Pixbuf but keeps its aspect ratio.
        Returns None if the pixbuf does not need to be
        resized or the newly resized pixbuf if it does.
        """
        if url in self._cover_cache:
            return self._cover_cache[url]

        max_side = self._max_image_side
        w_cur = pixbuf.get_width()
        h_cur = pixbuf.get_height()

        if w_cur <= max_side and h_cur <= max_side:
            return None

        f = max_side / (w_cur if w_cur >= h_cur else h_cur)
        w_new = int(w_cur * f)
        h_new = int(h_cur * f)

        logger.debug("Scaling cover image: url=%s from %ix%i to %ix%i",
                     url, w_cur, h_cur, w_new, h_new)
        pixbuf = pixbuf.scale_simple(w_new, h_new,
                                     GdkPixbuf.InterpType.BILINEAR)

        self._cover_cache[url] = pixbuf
        return pixbuf

    def _resize_pixbuf(self, url, pixbuf):
        if pixbuf is None:
            return None

        return self._resize_pixbuf_keep_ratio(url, pixbuf) or pixbuf

    def _overlay_pixbuf(self, pixbuf, icon):
        try:
            emblem = self.icon_theme.load_icon(icon, self._max_image_side / 2, 0)
            (width, height) = (emblem.get_width(), emblem.get_height())
            xpos = pixbuf.get_width() - width
            ypos = pixbuf.get_height() - height
            if ypos < 0:
                # need to resize overlay for none standard icon size
                emblem = self.icon_theme.load_icon(icon, pixbuf.get_height() - 1, 0)
                (width, height) = (emblem.get_width(), emblem.get_height())
                xpos = pixbuf.get_width() - width
                ypos = pixbuf.get_height() - height
            emblem.composite(pixbuf, xpos, ypos, width, height, xpos, ypos, 1, 1, GdkPixbuf.InterpType.BILINEAR, 255)
        except:
            pass

        return pixbuf

    def _get_cached_thumb(self, channel):
        if channel.cover_thumb is None:
            return None

        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(channel.cover_thumb)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if self._max_image_side not in (pixbuf.get_width(), pixbuf.get_height()):
                logger.debug("cached thumb wrong size: %r != %i", (pixbuf.get_width(), pixbuf.get_height()), self._max_image_side)
                return None
            return pixbuf
        except Exception as e:
            logger.warning('Could not load cached cover art for %s', channel.url, exc_info=True)
            channel.cover_thumb = None
            channel.save()
            return None

    def _save_cached_thumb(self, channel, pixbuf):
        bufs = []

        def save_callback(buf, length, user_data):
            user_data.append(buf)
            return True
        pixbuf.save_to_callbackv(save_callback, bufs, 'png', [None], [])
        channel.cover_thumb = bytes(b''.join(bufs))
        channel.save()

    def _get_cover_image(self, channel, add_overlay=False, pixbuf_overlay=None):
        """ get channel's cover image. Callable from gtk thread.
            :param channel: channel model
            :param bool add_overlay: True to add a pause/error overlay
            :param GdkPixbuf.Pixbux pixbuf_overlay: existing pixbuf if already loaded, as an optimization
            :return GdkPixbuf.Pixbux: channel's cover image as pixbuf
        """
        if self._cover_downloader is None:
            return pixbuf_overlay

        if pixbuf_overlay is None:  # optimization: we can pass existing pixbuf
            pixbuf_overlay = self._get_cached_thumb(channel)

        if pixbuf_overlay is None:
            # load cover if it's not in cache
            pixbuf = self._cover_downloader.get_cover(channel, avoid_downloading=True)
            if pixbuf is None:
                return None
            pixbuf_overlay = self._resize_pixbuf(channel.url, pixbuf)
            self._save_cached_thumb(channel, pixbuf_overlay)

        if add_overlay:
            if getattr(channel, '_update_error', None) is not None:
                pixbuf_overlay = self._overlay_pixbuf(pixbuf_overlay, self.ICON_ERROR)
            elif channel.pause_subscription:
                pixbuf_overlay = self._overlay_pixbuf(pixbuf_overlay, self.ICON_DISABLED)
                pixbuf_overlay.saturate_and_pixelate(pixbuf_overlay, 0.0, False)

        return pixbuf_overlay

    def _get_pill_image(self, channel, count_downloaded, count_unplayed):
        if count_unplayed > 0 or count_downloaded > 0:
            return draw.draw_pill_pixbuf('{:n}'.format(count_unplayed),
                                         '{:n}'.format(count_downloaded),
                                         widget=self.widget,
                                         scale=self._scale)
        else:
            return None

    def _format_description(self, channel, total, deleted,
            new, downloaded, unplayed):
        title_markup = html.escape(channel.title)
        if channel._update_error is not None:
            description_markup = html.escape(_('ERROR: %s') % channel._update_error)
        elif not channel.pause_subscription:
            description_markup = html.escape(
                util.get_first_line(util.remove_html_tags(channel.description)) or ' ')
        else:
            description_markup = html.escape(_('Subscription paused'))
        d = []
        if new:
            d.append('<span weight="bold">')
        d.append(title_markup)
        if new:
            d.append('</span>')

        if channel._update_error is not None:
            return ''.join(d + ['\n', '<span weight="bold">', description_markup, '</span>'])
        elif description_markup.strip():
            return ''.join(d + ['\n', '<small>', description_markup, '</small>'])
        else:
            return ''.join(d)

    def _format_error(self, channel):
        # if channel.parse_error:
        #     return str(channel.parse_error)
        # else:
        #     return None
        return None

    def set_channels(self, db, config, channels):
        # Clear the model and update the list of podcasts
        self.clear()

        def channel_to_row(channel, add_overlay=False):
            # C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL
            return (channel.url, '', '', None, channel,
                    # C_COVER, C_ERROR, C_PILL_VISIBLE,
                    self._get_cover_image(channel, add_overlay), '', True,
                    # C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED,
                    True, True,
                    # C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR
                    True, True, False,
                    # C_DOWNLOADS, C_COVER_VISIBLE, C_SECTION
                    0, True, '')

        def section_to_row(section):
            # C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL
            return (section.url, '', '', None, section,
                    # C_COVER, C_ERROR, C_PILL_VISIBLE,
                    None, '', True,
                    # C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED,
                    True, True,
                    # C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR
                    True, True, False,
                    # C_DOWNLOADS, C_COVER_VISIBLE, C_SECTION
                    0, False, section.title)

        if config.ui.gtk.podcast_list.all_episodes and channels:
            all_episodes = PodcastChannelProxy(db, config, channels, '', self)
            iter = self.append(channel_to_row(all_episodes))
            self.update_by_iter(iter)

            # Separator item
            if not config.ui.gtk.podcast_list.sections:
                self.append(('', '', '', None, SeparatorMarker, None, '',
                    True, True, True, True, True, True, 0, False, ''))

        def groupby_func(channel):
            return channel.group_by

        def key_func(channel):
            return (channel.group_by, model.Model.podcast_sort_key(channel))

        if config.ui.gtk.podcast_list.sections:
            groups = groupby(sorted(channels, key=key_func), groupby_func)
        else:
            groups = [(None, sorted(channels, key=model.Model.podcast_sort_key))]

        for section, section_channels in groups:
            if config.ui.gtk.podcast_list.sections and section is not None:
                section_channels = list(section_channels)
                section_obj = PodcastChannelProxy(db, config, section_channels, section, self)
                iter = self.append(section_to_row(section_obj))
                self.update_by_iter(iter)
            for channel in section_channels:
                iter = self.append(channel_to_row(channel, True))
                self.update_by_iter(iter)

    def get_filter_path_from_url(self, url):
        # Return the path of the filtered model for a given URL
        child_path = self.get_path_from_url(url)
        if child_path is None:
            return None
        else:
            return self._filter.convert_child_path_to_path(child_path)

    def get_path_from_url(self, url):
        # Return the tree model path for a given URL
        if url is None:
            return None

        for row in self:
            if row[self.C_URL] == url:
                return row.path
        return None

    def update_first_row(self):
        # Update the first row in the model (for "all episodes" updates)
        self.update_by_iter(self.get_iter_first())

    def update_by_urls(self, urls):
        # Given a list of URLs, update each matching row
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter)

    def iter_is_first_row(self, iter):
        iter = self._filter.convert_iter_to_child_iter(iter)
        path = self.get_path(iter)
        return (path == Gtk.TreePath.new_first())

    def update_by_filter_iter(self, iter):
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def update_all(self):
        for row in self:
            self.update_by_iter(row.iter)

    def update_sections(self):
        for row in self:
            if isinstance(row[self.C_CHANNEL], PodcastChannelProxy) and not row[self.C_CHANNEL].ALL_EPISODES_PROXY:
                self.update_by_iter(row.iter)

    def update_by_iter(self, iter):
        if iter is None:
            return

        # Given a GtkTreeIter, update volatile information
        channel = self.get_value(iter, self.C_CHANNEL)

        if channel is SeparatorMarker:
            return

        total, deleted, new, downloaded, unplayed = channel.get_statistics()

        if isinstance(channel, PodcastChannelProxy) and not channel.ALL_EPISODES_PROXY:
            section = channel.title

            # We could customized the section header here with the list
            # of channels and their stats (i.e. add some "new" indicator)
            description = '<b>%s</b>' % (
                    html.escape(section))
            pill_image = None
            cover_image = None
        else:
            description = self._format_description(channel, total, deleted, new,
                    downloaded, unplayed)

            pill_image = self._get_pill_image(channel, downloaded, unplayed)
            cover_image = self._get_cover_image(channel, True)

        self.set(iter,
                self.C_TITLE, channel.title,
                self.C_DESCRIPTION, description,
                self.C_COVER, cover_image,
                self.C_SECTION, channel.section,
                self.C_ERROR, self._format_error(channel),
                self.C_PILL, pill_image,
                self.C_PILL_VISIBLE, pill_image is not None,
                self.C_VIEW_SHOW_UNDELETED, total - deleted > 0,
                self.C_VIEW_SHOW_DOWNLOADED, downloaded + new > 0,
                self.C_VIEW_SHOW_UNPLAYED, unplayed + new > 0,
                self.C_HAS_EPISODES, total > 0,
                self.C_DOWNLOADS, downloaded)

    def clear_cover_cache(self, podcast_url):
        if podcast_url in self._cover_cache:
            logger.info('Clearing cover from cache: %s', podcast_url)
            del self._cover_cache[podcast_url]

    def add_cover_by_channel(self, channel, pixbuf):
        if pixbuf is None:
            return
        # Remove older images from cache
        self.clear_cover_cache(channel.url)

        # Resize and add the new cover image
        pixbuf = self._resize_pixbuf(channel.url, pixbuf)
        self._save_cached_thumb(channel, pixbuf)

        pixbuf = self._get_cover_image(channel, add_overlay=True, pixbuf_overlay=pixbuf)

        for row in self:
            if row[self.C_URL] == channel.url:
                row[self.C_COVER] = pixbuf
                break
