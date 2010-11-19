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
import pango
import xml.sax.saxutils

try:
    import gio
    have_gio = True
except ImportError:
    have_gio = False

class EpisodeListModel(gtk.GenericTreeModel):
    N_COLUMNS = 17

    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
            C_PUBLISHED_TEXT, C_DESCRIPTION, C_TOOLTIP, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_FILESIZE, C_PUBLISHED, \
            C_TIME, C_TIME1_VISIBLE, C_TIME2_VISIBLE, \
            C_LOCKED = range(N_COLUMNS)

    DATA_TYPES = (str, str, str, object, str   , str, str, \
            str, bool, bool, bool, int, int, str, bool, bool, \
            bool)

    SEARCH_COLUMNS = (C_TITLE,)

    VIEW_ALL, VIEW_UNDELETED, VIEW_DOWNLOADED, VIEW_UNPLAYED = range(4)

    # ---------------------

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return self.N_COLUMNS

    def on_get_column_type(self, index):
        return self.DATA_TYPES[index]

    def on_get_iter(self, path):
        return path[0]

    def on_get_path(self, rowref):
        return (rowref,)

    def on_get_value(self, rowref, column):
        if rowref >= len(self._episodes):
            return None

        episode = self._episodes[rowref]
        downloading = self._downloading

        if column == self.C_URL:
            return episode.url
        elif column == self.C_TITLE:
            return episode.title
        elif column == self.C_FILESIZE_TEXT:
            return self._format_filesize(episode)
        elif column == self.C_EPISODE:
            return episode
        elif column == self.C_STATUS_ICON:
            if downloading(episode):
                return self.ICON_DOWNLOADING
            elif episode.state == gpodder.STATE_DELETED:
                return self.ICON_DELETED
            elif episode.state == gpodder.STATE_NORMAL and \
                    not episode.is_played and \
                    not downloading(episode):
                return self.ICON_NEW
            elif episode.state == gpodder.STATE_DOWNLOADED:
                filename = episode.local_filename(create=False, \
                        check_only=True)

                file_type = episode.file_type()
                if file_type == 'audio':
                    status_icon = self.ICON_AUDIO_FILE
                elif file_type == 'video':
                    status_icon = self.ICON_VIDEO_FILE
                elif file_type == 'image':
                    status_icon = self.ICON_IMAGE_FILE
                else:
                    status_icon = self.ICON_GENERIC_FILE

                if gpodder.ui.maemo:
                    return status_icon

                icon_theme = gtk.icon_theme_get_default()
                if filename is not None and have_gio:
                    file = gio.File(filename)
                    if file.query_exists():
                        file_info = file.query_info('*')
                        icon = file_info.get_icon()
                        for icon_name in icon.get_names():
                            if icon_theme.has_icon(icon_name):
                                return icon_name

                return status_icon

            return None
        elif column == self.C_PUBLISHED_TEXT:
            return episode.cute_pubdate()
        elif column == self.C_DESCRIPTION:
            return self._format_description(episode, \
                    self._include_description, \
                    self._downloading)
        elif column == self.C_TOOLTIP:
            if downloading(episode):
                return _('Downloading')
            elif episode.state == gpodder.STATE_DELETED:
                return _('Deleted')
            elif episode.state == gpodder.STATE_NORMAL and \
                    not episode.is_played:
                return _('New episode')
            elif episode.state == gpodder.STATE_DOWNLOADED:
                file_type = episode.file_type()
                if not episode.file_exists():
                    return _('missing file')
                if file_type == 'audio':
                    return _('Downloaded episode')
                elif file_type == 'video':
                    return _('Downloaded video episode')
                elif file_type == 'image':
                    return _('Downloaded image')
                else:
                    return _('Downloaded file')

            return ''
        elif column == self.C_VIEW_SHOW_UNDELETED:
            return episode.state != gpodder.STATE_DELETED or downloading(episode)
        elif column == self.C_VIEW_SHOW_DOWNLOADED:
            return episode.state == gpodder.STATE_DOWNLOADED or \
                    (episode.state == gpodder.STATE_NORMAL and \
                     not episode.is_played) or \
                    downloading(episode)
        elif column == self.C_VIEW_SHOW_UNPLAYED:
            return (not episode.is_played and (episode.state in \
                    (gpodder.STATE_DOWNLOADED, gpodder.STATE_NORMAL))) or \
                    downloading(episode)
        elif column == self.C_FILESIZE:
            return episode.length
        elif column == self.C_PUBLISHED:
            return episode.pubDate
        elif column == self.C_TIME:
            return episode.get_play_info_string()
        elif column == self.C_TIME1_VISIBLE:
            return (episode.total_time and not episode.current_position)
        elif column == self.C_TIME2_VISIBLE:
            return (episode.total_time and episode.current_position)
        elif column == self.C_LOCKED:
            return episode.is_locked and \
                    episode.state== gpodder.STATE_DOWNLOADED and \
                    episode.file_exists()

        raise Exception('could not find column index: ' + str(column))

    def on_iter_next(self, rowref):
        if len(self._episodes) > rowref + 1:
            return rowref + 1

        return None

    def on_iter_children(self, parent):
        if parent is None:
            if self._episodes:
                return 0

        return None

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        if rowref is None:
            return len(self._episodes)

        return 0

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            return n

        return None

    def on_iter_parent(self, child):
        return None

    # ---------------------


    def __init__(self):
        gtk.GenericTreeModel.__init__(self)

        self._downloading = None
        self._include_description = False
        self._generate_thumbnails = False

        self._episodes = []

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
        self.ICON_UNPLAYED = ICON('emblem-new')
        self.ICON_LOCKED = ICON('emblem-readonly')
        self.ICON_MISSING = ICON('emblem-unreadable')
        self.ICON_NEW = gtk.STOCK_ABOUT

        if gpodder.ui.fremantle:
            self.ICON_AUDIO_FILE = ICON('general_audio_file')
            self.ICON_VIDEO_FILE = ICON('general_video_file')
            self.ICON_IMAGE_FILE = ICON('general_image')
            self.ICON_GENERIC_FILE = ICON('filemanager_unknown_file')
            self.ICON_DOWNLOADING = ICON('email_inbox')
            self.ICON_DELETED = ICON('camera_delete_dimmed')

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

    def _format_description(self, episode, include_description=False, is_downloading=None):
        if include_description and self._all_episodes_view:
            return '%s\n<small>%s</small>' % (xml.sax.saxutils.escape(episode.title),
                    _('from %s') % xml.sax.saxutils.escape(episode.channel.title))
        elif include_description:
            return '%s\n<small>%s</small>' % (xml.sax.saxutils.escape(episode.title),
                    xml.sax.saxutils.escape(episode.one_line_description()))
        else:
            return xml.sax.saxutils.escape(episode.title)

    def clear(self):
        count = len(self._episodes)
        for i in reversed(range(count)):
            self.emit('row-deleted', (i,))
            self._episodes.pop()

    def replace_from_channel(self, channel, downloading=None, \
            include_description=False, generate_thumbnails=False):
        """
        Add episode from the given channel to this model.
        Downloading should be a callback.
        include_description should be a boolean value (True if description
        is to be added to the episode row, or False if not)
        """

        self._downloading = downloading
        self._include_description = include_description
        self._generate_thumbnails = generate_thumbnails

        self._all_episodes_view = getattr(channel, 'ALL_EPISODES_PROXY', False)

        old_length = len(self._episodes)
        self._episodes = channel.get_all_episodes()
        new_length = len(self._episodes)

        for i in range(min(old_length, new_length)):
            self.emit('row-changed', (i,), self.create_tree_iter(i))

        if old_length > new_length:
            for i in reversed(range(new_length, old_length)):
                self.emit('row-deleted', (i,))
        elif old_length < new_length:
            for i in range(old_length, new_length):
                self.emit('row-inserted', (i,), self.create_tree_iter(i))


    def update_all(self, downloading=None, include_description=False, \
            generate_thumbnails=False):

        self._downloading = downloading
        self._include_description = include_description
        self._generate_thumbnails = generate_thumbnails

        for i in range(len(self._episodes)):
            self.emit('row-changed', (i,), self.create_tree_iter(i))

    def update_by_urls(self, urls, downloading=None, include_description=False, \
            generate_thumbnails=False):

        self._downloading = downloading
        self._include_description = include_description
        self._generate_thumbnails = generate_thumbnails

        for index, episode in enumerate(self._episodes):
            if episode.url in urls:
                self.emit('row-changed', (index,), self.create_tree_iter(index))

    def update_by_filter_iter(self, iter, downloading=None, \
            include_description=False, generate_thumbnails=False):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
        iter = self._sorter.convert_iter_to_child_iter(None, iter)
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter), \
                downloading, include_description, generate_thumbnails)

    def update_by_iter(self, iter, downloading=None, include_description=False, \
            generate_thumbnails=False, reload_from_db=True):

        self._downloading = downloading
        self._include_description = include_description
        self._generate_thumbnails = generate_thumbnails

        index = self.get_user_data(iter)
        episode = self._episodes[index]
        if reload_from_db:
            episode.reload_from_db()

        self.emit('row-changed', (index,), self.create_tree_iter(index))

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


class PodcastListModel(gtk.GenericTreeModel):
    N_COLUMNS = 14

    C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL, \
            C_COVER, C_ERROR, C_PILL_VISIBLE, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR, \
            C_DOWNLOADS = range(N_COLUMNS)

    DATA_TYPES = (str, str, str, gtk.gdk.Pixbuf, object, \
            gtk.gdk.Pixbuf, str, bool, bool, bool, bool, \
            bool, bool, int)

    SEARCH_COLUMNS = (C_TITLE,)

    class Separator: pass

    # ---------------------

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return self.N_COLUMNS

    def on_get_column_type(self, index):
        return self.DATA_TYPES[index]

    def on_get_iter(self, path):
        return path[0]

    def on_get_path(self, rowref):
        return (rowref,)

    def on_get_value(self, rowref, column):
        if rowref >= len(self._podcasts):
            return None

        channel = self._podcasts[rowref]

        if channel is self.Separator and column != self.C_SEPARATOR:
            return None

        if column == self.C_URL:
            return channel.url
        elif column == self.C_TITLE:
            return channel.title
        elif column == self.C_DESCRIPTION:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return self._format_description(channel, total, deleted, new, \
                    downloaded, unplayed)
        elif column == self.C_PILL:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return self._get_pill_image(channel, downloaded, unplayed)
        elif column == self.C_CHANNEL:
            return channel
        elif column == self.C_COVER:
            return self._get_cover_image(channel, True)
        elif column == self.C_ERROR:
            return self._format_error(channel)
        elif column == self.C_PILL_VISIBLE:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return (unplayed > 0 or downloaded > 0)
        elif column == self.C_VIEW_SHOW_UNDELETED:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return (total - deleted > 0)
        elif column == self.C_VIEW_SHOW_DOWNLOADED:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return (downloaded + new > 0)
        elif column == self.C_VIEW_SHOW_UNPLAYED:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return (unplayed + new > 0)
        elif column == self.C_HAS_EPISODES:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return total > 0
        elif column == self.C_SEPARATOR:
            return (channel is self.Separator)
        elif column == self.C_DOWNLOADS:
            total, deleted, new, downloaded, unplayed = channel.get_statistics()
            return downloaded

        raise Exception('could not find column index: ' + str(column))

    def on_iter_next(self, rowref):
        if len(self._podcasts) > rowref + 1:
            return rowref + 1

        return None

    def on_iter_children(self, parent):
        if parent is None:
            if len(self._podcasts):
                return 0

        return None

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        if rowref is None:
            return len(self._podcasts)

        return 0

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            return n

        return None

    def on_iter_parent(self, child):
        return None

    # ---------------------

    @classmethod
    def row_separator_func(cls, model, iter):
        return model.get_value(iter, cls.C_SEPARATOR)

    def __init__(self, cover_downloader):
        gtk.GenericTreeModel.__init__(self)

        # The internal data storage - a simple list of podcasts
        self._podcasts = []
        self._coverart = {}

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
        old_length = len(self._podcasts)
        self._podcasts = [PodcastChannelProxy(db, config, channels), \
                self.Separator] + channels
        new_length = len(self._podcasts)

        for i in range(min(old_length, new_length)):
            self.emit('row-changed', (i,), self.create_tree_iter(i))

        if old_length > new_length:
            for i in reversed(range(new_length, old_length)):
                self.emit('row-deleted', (i,))
        elif old_length < new_length:
            for i in range(old_length, new_length):
                self.emit('row-inserted', (i,), self.create_tree_iter(i))

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

        for index, channel in enumerate(self._podcasts):
            if channel.url == url:
                return (index,)

        return None

    def update_first_row(self):
        # Update the first row in the model (for "all episodes" updates)
        self.emit('row-changed', (0,), self.create_tree_iter(0))

    def update_by_urls(self, urls):
        # Given a list of URLs, update each matching row
        for index, channel in enumerate(self._podcasts):
            if channel is self.Separator:
                continue
            if channel.url in urls:
                self.emit('row-changed', (index,), self.create_tree_iter(index))

    def iter_is_first_row(self, iter):
        iter = self._filter.convert_iter_to_child_iter(iter)
        path = self.get_path(iter)
        return (path == (0,))

    def update_by_filter_iter(self, iter):
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def update_all(self):
        for i in range(len(self._podcasts)):
            self.emit('row-changed', (i,), self.create_tree_iter(i))

    def update_by_iter(self, iter):
        iter = self.get_user_data(iter)
        self.emit('row-changed', (iter,), self.create_tree_iter(iter))

    def add_cover_by_channel(self, channel, pixbuf):
        # Resize and add the new cover image
        pixbuf = self._resize_pixbuf(channel.url, pixbuf)
        if not channel.feed_update_enabled:
            pixbuf = self._overlay_pixbuf(pixbuf, self.ICON_DISABLED)
            pixbuf.saturate_and_pixelate(pixbuf, 0.0, False)

        for index, chan in enumerate(self._podcasts):
            if chan is self.Separator:
                continue
            if channel.url == chan.url:
                self.emit('row-changed', (index,), \
                        self.create_tree_iter(index))

    def delete_cover_by_url(self, url):
        if url in self._cover_cache:
            del self._cover_cache[url]

            for index, channel in enumerate(self._podcasts):
                if channel is self.Separator:
                    continue
                if url == channel.url:
                    self.emit('row-changed', (index,), \
                            self.create_tree_iter(index))

