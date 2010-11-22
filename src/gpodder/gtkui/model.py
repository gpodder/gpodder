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
#  gpodder.gtkui.model - GUI model classes for gPodder (2009-08-13)
#  Based on code from libpodcasts.py (thp, 2005-10-29)
#

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder.liblogger import log

from gpodder.gtkui import draw

import os
import gtk
import xml.sax.saxutils

try:
    import gio
    have_gio = True
except ImportError:
    have_gio = False

class EpisodeListModel(gtk.ListStore):
    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
            C_PUBLISHED_TEXT, C_DESCRIPTION, C_TOOLTIP, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_FILESIZE, C_PUBLISHED, \
            C_TIME, C_TIME1_VISIBLE, C_TIME2_VISIBLE, \
            C_LOCKED = range(17)

    SEARCH_COLUMNS = (C_TITLE, C_DESCRIPTION)

    VIEW_ALL, VIEW_UNDELETED, VIEW_DOWNLOADED, VIEW_UNPLAYED = range(4)

    # In which steps the UI is updated for "loading" animations
    _UI_UPDATE_STEP = .03

    def __init__(self, on_filter_changed=lambda has_episodes: None):
        gtk.ListStore.__init__(self, str, str, str, object, \
                str, str, str, str, bool, bool, bool, \
                int, int, str, bool, bool, bool)

        # Callback for when the filter / list changes, gets one parameter
        # (has_episodes) that is True if the list has any episodes
        self._on_filter_changed = on_filter_changed

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._sorter = gtk.TreeModelSort(self._filter)
        self._view_mode = self.VIEW_ALL
        self._search_term = None
        self._filter.set_visible_func(self._filter_visible_func)

        # Are we currently showing the "all episodes" view?
        self._all_episodes_view = False

        # "ICON" is used to mark icon names in source files
        ICON = lambda x: x

        self._icon_cache = {}
        self.ICON_AUDIO_FILE = ICON('audio-x-generic')
        self.ICON_VIDEO_FILE = ICON('video-x-generic')
        self.ICON_IMAGE_FILE = ICON('image-x-generic')
        self.ICON_GENERIC_FILE = ICON('text-x-generic')
        self.ICON_DOWNLOADING = gtk.STOCK_GO_DOWN
        self.ICON_DELETED = gtk.STOCK_DELETE
        self.ICON_NEW = gtk.STOCK_ABOUT
        self.ICON_UNPLAYED = ICON('emblem-new')
        self.ICON_LOCKED = ICON('emblem-readonly')
        self.ICON_MISSING = ICON('emblem-unreadable')

        if 'KDE_FULL_SESSION' in os.environ:
            # Workaround until KDE adds all the freedesktop icons
            # See https://bugs.kde.org/show_bug.cgi?id=233505 and
            #     http://gpodder.org/bug/553
            self.ICON_DELETED = ICON('archive-remove')
            self.ICON_UNPLAYED = ICON('vcs-locally-modified')
            self.ICON_LOCKED = ICON('emblem-locked')
            self.ICON_MISSING = ICON('vcs-conflicting')


    def _format_filesize(self, episode):
        if episode.length > 0:
            return util.format_filesize(episode.length, 1)
        else:
            return None


    def _filter_visible_func(self, model, iter):
        # If searching is active, set visibility based on search text
        if self._search_term is not None:
            key = self._search_term.lower()
            return any((key in (model.get_value(iter, column) or '').lower()) for column in self.SEARCH_COLUMNS)

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
            self._filter.refilter()
            self._on_filter_changed(self.has_episodes())

    def get_search_term(self):
        return self._search_term

    def _format_description(self, episode, include_description=False, is_downloading=None):
        a, b = '', ''
        if episode.state != gpodder.STATE_DELETED and not episode.is_played:
            a, b = '<b>', '</b>'
        if include_description and self._all_episodes_view:
            return '%s%s%s\n<small>%s</small>' % (a, xml.sax.saxutils.escape(episode.title), b,
                    _('from %s') % xml.sax.saxutils.escape(episode.channel.title))
        elif include_description:
            return '%s%s%s\n<small>%s</small>' % (a, xml.sax.saxutils.escape(episode.title), b,
                    xml.sax.saxutils.escape(episode.one_line_description()))
        else:
            return xml.sax.saxutils.escape(episode.title)

    def replace_from_channel(self, channel, downloading=None, \
            include_description=False, generate_thumbnails=False, \
            treeview=None):
        """
        Add episode from the given channel to this model.
        Downloading should be a callback.
        include_description should be a boolean value (True if description
        is to be added to the episode row, or False if not)
        """

        # Remove old episodes in the list store
        self.clear()

        if treeview is not None:
            util.idle_add(treeview.queue_draw)

        self._all_episodes_view = getattr(channel, 'ALL_EPISODES_PROXY', False)

        episodes = channel.get_all_episodes()
        if not isinstance(episodes, list):
            episodes = list(episodes)
        count = len(episodes)

        for position, episode in enumerate(episodes):
            iter = self.append((episode.url, \
                    episode.title, \
                    self._format_filesize(episode), \
                    episode, \
                    None, \
                    episode.cute_pubdate(), \
                    '', \
                    '', \
                    True, \
                    True, \
                    True, \
                    episode.length, \
                    episode.pubDate, \
                    episode.get_play_info_string(), \
                    episode.total_time and not episode.current_position, \
                    episode.total_time and episode.current_position, \
                    episode.is_locked))

            self.update_by_iter(iter, downloading, include_description, \
                    generate_thumbnails, reload_from_db=False)

        self._on_filter_changed(self.has_episodes())

    def update_all(self, downloading=None, include_description=False, \
            generate_thumbnails=False):
        for row in self:
            self.update_by_iter(row.iter, downloading, include_description, \
                    generate_thumbnails)

    def update_by_urls(self, urls, downloading=None, include_description=False, \
            generate_thumbnails=False):
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter, downloading, include_description, \
                        generate_thumbnails)

    def update_by_filter_iter(self, iter, downloading=None, \
            include_description=False, generate_thumbnails=False):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
        iter = self._sorter.convert_iter_to_child_iter(None, iter)
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter), \
                downloading, include_description, generate_thumbnails)

    def update_by_iter(self, iter, downloading=None, include_description=False, \
            generate_thumbnails=False, reload_from_db=True):
        episode = self.get_value(iter, self.C_EPISODE)
        if reload_from_db:
            episode.reload_from_db()

        if include_description or gpodder.ui.maemo:
            icon_size = 32
        else:
            icon_size = 16

        show_bullet = False
        show_padlock = False
        show_missing = False
        status_icon = None
        status_icon_to_build_from_file = False
        tooltip = []
        view_show_undeleted = True
        view_show_downloaded = False
        view_show_unplayed = False
        icon_theme = gtk.icon_theme_get_default()

        if downloading is not None and downloading(episode):
            tooltip.append(_('Downloading'))
            status_icon = self.ICON_DOWNLOADING
            view_show_downloaded = True
            view_show_unplayed = True
        else:
            if episode.state == gpodder.STATE_DELETED:
                tooltip.append(_('Deleted'))
                status_icon = self.ICON_DELETED
                view_show_undeleted = False
            elif episode.state == gpodder.STATE_NORMAL and \
                    not episode.is_played:
                tooltip.append(_('New episode'))
                status_icon = self.ICON_NEW
                view_show_downloaded = True
                view_show_unplayed = True
            elif episode.state == gpodder.STATE_DOWNLOADED:
                tooltip = []
                view_show_downloaded = True
                view_show_unplayed = not episode.is_played
                show_bullet = not episode.is_played
                show_padlock = episode.is_locked
                show_missing = not episode.file_exists()
                filename = episode.local_filename(create=False, check_only=True)

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

                    # Optional thumbnailing for image downloads
                    if generate_thumbnails:
                        if filename is not None:
                            # set the status icon to the path itself (that
                            # should be a good identifier anyway)
                            status_icon = filename
                            status_icon_to_build_from_file = True
                else:
                    tooltip.append(_('Downloaded file'))
                    status_icon = self.ICON_GENERIC_FILE

                # Try to find a themed icon for this file
                if filename is not None and have_gio:
                    file = gio.File(filename)
                    if file.query_exists():
                        file_info = file.query_info('*')
                        icon = file_info.get_icon()
                        for icon_name in icon.get_names():
                            if icon_theme.has_icon(icon_name):
                                status_icon = icon_name
                                break

                if show_missing:
                    tooltip.append(_('missing file'))
                else:
                    if show_bullet:
                        if file_type == 'image':
                            tooltip.append(_('never displayed'))
                        elif file_type in ('audio', 'video'):
                            tooltip.append(_('never played'))
                        else:
                            tooltip.append(_('never opened'))
                    else:
                        if file_type == 'image':
                            tooltip.append(_('displayed'))
                        elif file_type in ('audio', 'video'):
                            tooltip.append(_('played'))
                        else:
                            tooltip.append(_('opened'))
                    if show_padlock:
                        tooltip.append(_('deletion prevented'))

                if episode.total_time > 0 and episode.current_position:
                    tooltip.append('%d%%' % (100.*float(episode.current_position)/float(episode.total_time),))

        if episode.total_time:
            total_time = util.format_time(episode.total_time)
            if total_time:
                tooltip.append(total_time)

        tooltip = ', '.join(tooltip)

        description = self._format_description(episode, include_description, downloading)
        self.set(iter, \
                self.C_STATUS_ICON, status_icon, \
                self.C_VIEW_SHOW_UNDELETED, view_show_undeleted, \
                self.C_VIEW_SHOW_DOWNLOADED, view_show_downloaded, \
                self.C_VIEW_SHOW_UNPLAYED, view_show_unplayed, \
                self.C_DESCRIPTION, description, \
                self.C_TOOLTIP, tooltip, \
                self.C_TIME, episode.get_play_info_string(), \
                self.C_TIME1_VISIBLE, episode.total_time and not episode.current_position, \
                self.C_TIME2_VISIBLE, episode.total_time and episode.current_position, \
                self.C_LOCKED, episode.is_locked)

    def _get_icon_from_image(self,image_path, icon_size):
        """
        Load an local image file and transform it into an icon.

        Return a pixbuf scaled to the desired size and may return None
        if the icon creation is impossible (file not found etc).
        """
        if not os.path.exists(image_path):
            return None
        # load image from disc (code adapted from CoverDownloader
        # except that no download is needed here)
        loader = gtk.gdk.PixbufLoader()
        pixbuf = None
        try:
            loader.write(open(image_path, 'rb').read())
            loader.close()
            pixbuf = loader.get_pixbuf()
        except:
            log('Data error while loading image %s', image_path, sender=self)
            return None
        # Now scale the image with ratio (copied from _resize_pixbuf_keep_ratio)
        # Resize if too wide
        if pixbuf.get_width() > icon_size:
            f = float(icon_size)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
        # Resize if too high
        if pixbuf.get_height() > icon_size:
            f = float(icon_size)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
        return pixbuf
        
        
    def _get_tree_icon(self, icon_name, add_bullet=False, \
            add_padlock=False, add_missing=False, icon_size=32, \
            build_icon_from_file = False):
        """
        Loads an icon from the current icon theme at the specified
        size, suitable for display in a gtk.TreeView. Additional
        emblems can be added on top of the icon.

        Caching is used to speed up the icon lookup.
        
        The `build_icon_from_file` argument indicates (when True) that
        the icon has to be created on the fly from a given image
        file. The `icon_name` argument is then interpreted as the path
        to this file. Those specific icons will *not be cached*.
        """
        
        # Add all variables that modify the appearance of the icon, so
        # our cache does not return the same icons for different requests
        cache_id = (icon_name, add_bullet, add_padlock, add_missing, icon_size)

        if cache_id in self._icon_cache:
            return self._icon_cache[cache_id]

        icon_theme = gtk.icon_theme_get_default()

        try:
            if build_icon_from_file:
                icon = self._get_icon_from_image(icon_name,icon_size)
            else:
                icon = icon_theme.load_icon(icon_name, icon_size, 0)
        except:
            try:
                log('Missing icon in theme: %s', icon_name, sender=self)
                icon = icon_theme.load_icon(gtk.STOCK_DIALOG_QUESTION, \
                        icon_size, 0)
            except:
                log('Please install the GNOME icon theme.', sender=self)
                icon = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, \
                        True, 8, icon_size, icon_size)

        if icon and (add_bullet or add_padlock or add_missing):
            # We'll modify the icon, so use .copy()
            if add_missing:
                try:
                    icon = icon.copy()
                    # Desaturate the icon so it looks even more "missing"
                    icon.saturate_and_pixelate(icon, 0.0, False)
                    emblem = icon_theme.load_icon(self.ICON_MISSING, icon_size/2, 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    xpos = icon.get_width() - width
                    ypos = icon.get_height() - height
                    emblem.composite(icon, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass
            elif add_bullet:
                try:
                    icon = icon.copy()
                    emblem = icon_theme.load_icon(self.ICON_UNPLAYED, icon_size/2, 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    xpos = icon.get_width() - width
                    ypos = icon.get_height() - height
                    emblem.composite(icon, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass
            if add_padlock:
                try:
                    icon = icon.copy()
                    emblem = icon_theme.load_icon(self.ICON_LOCKED, icon_size/2, 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    emblem.composite(icon, 0, 0, width, height, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass

        self._icon_cache[cache_id] = icon
        return icon


class PodcastChannelProxy(object):
    ALL_EPISODES_PROXY = True

    def __init__(self, db, config, channels):
        self._db = db
        self._config = config
        self.channels = channels
        self.title =  _('All episodes')
        self.description = _('from all podcasts')
        self.parse_error = ''
        self.url = ''
        self.id = None
        self._save_dir_size_set = False
        self.save_dir_size = 0L
        self.cover_file = os.path.join(gpodder.images_folder, 'podcast-all.png')
        self.feed_update_enabled = True

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            log('Unsupported method call (%s)', name, sender=self)

    def get_statistics(self):
        # Get the total statistics for all channels from the database
        return self._db.get_total_count()

    def get_all_episodes(self):
        """Returns a generator that yields every episode"""
        channel_lookup_map = dict((c.id, c) for c in self.channels)
        return self._db.load_all_episodes(channel_lookup_map)

    def request_save_dir_size(self):
        if not self._save_dir_size_set:
            self.update_save_dir_size()
        self._save_dir_size_set = True

    def update_save_dir_size(self):
        self.save_dir_size = util.calculate_size(self._config.download_dir)


class PodcastListModel(gtk.ListStore):
    C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL, \
            C_COVER, C_ERROR, C_PILL_VISIBLE, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR, \
            C_DOWNLOADS = range(14)

    SEARCH_COLUMNS = (C_TITLE, C_DESCRIPTION)

    @classmethod
    def row_separator_func(cls, model, iter):
        return model.get_value(iter, cls.C_SEPARATOR)

    def __init__(self, cover_downloader):
        gtk.ListStore.__init__(self, str, str, str, gtk.gdk.Pixbuf, \
                object, gtk.gdk.Pixbuf, str, bool, bool, bool, bool, \
                bool, bool, int)

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = -1
        self._search_term = None
        self._filter.set_visible_func(self._filter_visible_func)

        self._cover_cache = {}
        if gpodder.ui.fremantle:
            self._max_image_side = 64
        else:
            self._max_image_side = 40
        self._cover_downloader = cover_downloader

        # "ICON" is used to mark icon names in source files
        ICON = lambda x: x

        #self.ICON_DISABLED = ICON('emblem-unreadable')
        self.ICON_DISABLED = ICON('gtk-media-pause')

    def _filter_visible_func(self, model, iter):
        # If searching is active, set visibility based on search text
        if self._search_term is not None:
            key = self._search_term.lower()
            columns = (model.get_value(iter, c) for c in self.SEARCH_COLUMNS)
            return any((key in c.lower() for c in columns if c is not None))

        if model.get_value(iter, self.C_SEPARATOR):
            return True
        if self._view_mode == EpisodeListModel.VIEW_ALL:
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

    def enable_separators(self, channeltree):
        channeltree.set_row_separator_func(self._show_row_separator)

    def _show_row_separator(self, model, iter):
        return model.get_value(iter, self.C_SEPARATOR)

    def _resize_pixbuf_keep_ratio(self, url, pixbuf):
        """
        Resizes a GTK Pixbuf but keeps its aspect ratio.
        Returns None if the pixbuf does not need to be
        resized or the newly resized pixbuf if it does.
        """
        changed = False
        result = None

        if url in self._cover_cache:
            return self._cover_cache[url]

        # Resize if too wide
        if pixbuf.get_width() > self._max_image_side:
            f = float(self._max_image_side)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            changed = True

        # Resize if too high
        if pixbuf.get_height() > self._max_image_side:
            f = float(self._max_image_side)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            changed = True

        if changed:
            self._cover_cache[url] = pixbuf
            result = pixbuf

        return result

    def _resize_pixbuf(self, url, pixbuf):
        if pixbuf is None:
            return None

        return self._resize_pixbuf_keep_ratio(url, pixbuf) or pixbuf

    def _overlay_pixbuf(self, pixbuf, icon):
        try:
            icon_theme = gtk.icon_theme_get_default()
            emblem = icon_theme.load_icon(icon, self._max_image_side/2, 0)
            (width, height) = (emblem.get_width(), emblem.get_height())
            xpos = pixbuf.get_width() - width
            ypos = pixbuf.get_height() - height
            if ypos < 0:
                # need to resize overlay for none standard icon size
                emblem = icon_theme.load_icon(icon, pixbuf.get_height() - 1, 0)
                (width, height) = (emblem.get_width(), emblem.get_height())
                xpos = pixbuf.get_width() - width
                ypos = pixbuf.get_height() - height
            emblem.composite(pixbuf, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        except:
            pass

        return pixbuf

    def _get_cover_image(self, channel, add_overlay=False):
        if self._cover_downloader is None:
            return None

        pixbuf = self._cover_downloader.get_cover(channel, avoid_downloading=True)
        pixbuf_overlay = self._resize_pixbuf(channel.url, pixbuf)
        if add_overlay and not channel.feed_update_enabled:
            pixbuf_overlay = self._overlay_pixbuf(pixbuf_overlay, self.ICON_DISABLED)
            pixbuf_overlay.saturate_and_pixelate(pixbuf_overlay, 0.0, False)

        return pixbuf_overlay

    def _get_pill_image(self, channel, count_downloaded, count_unplayed):
        if count_unplayed > 0 or count_downloaded > 0:
            return draw.draw_pill_pixbuf(str(count_unplayed), str(count_downloaded))
        else:
            return None

    def _format_description(self, channel, total, deleted, \
            new, downloaded, unplayed):
        title_markup = xml.sax.saxutils.escape(channel.title)
        if channel.feed_update_enabled:
            description_markup = xml.sax.saxutils.escape(util.get_first_line(channel.description) or ' ')
        else:
            description_markup = xml.sax.saxutils.escape(_('Subscription paused.'))
        d = []
        if new:
            d.append('<span weight="bold">')
        d.append(title_markup)
        if new:
            d.append('</span>')
        return ''.join(d+['\n', '<small>', description_markup, '</small>'])

    def _format_error(self, channel):
        if channel.parse_error:
            return str(channel.parse_error)
        else:
            return None

    def set_channels(self, db, config, channels):
        # Clear the model and update the list of podcasts
        self.clear()

        def channel_to_row(channel, add_overlay=False):
            return (channel.url, '', '', None, channel, \
                    self._get_cover_image(channel, add_overlay), '', True, True, True, \
                    True, True, False, 0)

        if config.podcast_list_view_all and channels:
            all_episodes = PodcastChannelProxy(db, config, channels)
            iter = self.append(channel_to_row(all_episodes))
            self.update_by_iter(iter)

            # Separator item
            self.append(('', '', '', None, None, None, '', True, True, \
                    True, True, True, True, 0))

        for channel in channels:
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
        return (path == (0,))

    def update_by_filter_iter(self, iter):
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def update_all(self):
        for row in self:
            self.update_by_iter(row.iter)

    def update_by_iter(self, iter):
        # Given a GtkTreeIter, update volatile information
        try:
            channel = self.get_value(iter, self.C_CHANNEL)
        except TypeError, te:
            return
        if channel is None:
            return
        total, deleted, new, downloaded, unplayed = channel.get_statistics()
        description = self._format_description(channel, total, deleted, new, \
                downloaded, unplayed)

        if gpodder.ui.fremantle:
            # We don't display the pill, so don't generate it
            pill_image = None
        else:
            pill_image = self._get_pill_image(channel, downloaded, unplayed)

        self.set(iter, \
                self.C_TITLE, channel.title, \
                self.C_DESCRIPTION, description, \
                self.C_ERROR, self._format_error(channel), \
                self.C_PILL, pill_image, \
                self.C_PILL_VISIBLE, pill_image != None, \
                self.C_VIEW_SHOW_UNDELETED, total - deleted > 0, \
                self.C_VIEW_SHOW_DOWNLOADED, downloaded + new > 0, \
                self.C_VIEW_SHOW_UNPLAYED, unplayed + new > 0, \
                self.C_HAS_EPISODES, total > 0, \
                self.C_DOWNLOADS, downloaded)

    def add_cover_by_channel(self, channel, pixbuf):
        # Resize and add the new cover image
        pixbuf = self._resize_pixbuf(channel.url, pixbuf)
        if not channel.feed_update_enabled:
            pixbuf = self._overlay_pixbuf(pixbuf, self.ICON_DISABLED)
            pixbuf.saturate_and_pixelate(pixbuf, 0.0, False)

        for row in self:
            if row[self.C_URL] == channel.url:
                row[self.C_COVER] = pixbuf
                break

    def delete_cover_by_url(self, url):
        # Remove the cover from the model
        for row in self:
            if row[self.C_URL] == url:
                row[self.C_COVER] = None
                break

        # Remove the cover from the cache
        if url in self._cover_cache:
            del self._cover_cache[url]

