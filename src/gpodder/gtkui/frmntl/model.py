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
#  gpodder.gtkui.frmntl.model -- Model customizations for Maemo 5 (2009-11-16)
#

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

import cgi
import gtk

from gpodder.gtkui import download
from gpodder.gtkui import model
from gpodder.gtkui.frmntl import style

from gpodder import util
from gpodder import query

class DownloadStatusModel(download.DownloadStatusModel):
    def __init__(self):
        download.DownloadStatusModel.__init__(self)
        head_font = style.get_font_desc('SystemFont')
        head_color = style.get_color('ButtonTextColor')
        head = (head_font.to_string(), head_color.to_string())
        head = '<span font_desc="%s" foreground="%s">%%s</span>' % head
        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        sub = '<span font_desc="%s" foreground="%s">%%s - %%s</span>' % sub
        self._markup_template = '\n'.join((head, sub))

    def _format_message(self, episode, message, podcast):
        return self._markup_template % (episode, message, podcast)


class EpisodeListModel(gtk.GenericTreeModel):
    N_COLUMNS = 16

    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
            C_PUBLISHED_TEXT, C_DESCRIPTION, C_TOOLTIP, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_FILESIZE, C_PUBLISHED, \
            C_TIME, C_TIME_VISIBLE, \
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

                return status_icon

            return None
        elif column == self.C_PUBLISHED_TEXT:
            return episode.cute_pubdate()
        elif column == self.C_DESCRIPTION:
            return self._format_description(episode)
        elif column == self.C_TOOLTIP:
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
            return episode.file_size
        elif column == self.C_PUBLISHED:
            return episode.published
        elif column == self.C_TIME:
            return episode.get_play_info_string()
        elif column == self.C_TIME_VISIBLE:
            return episode.total_time
        elif column == self.C_LOCKED:
            return episode.is_locked and \
                    episode.state == gpodder.STATE_DOWNLOADED and \
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


    def __init__(self, on_filter_changed=lambda has_episodes: None):
        gtk.GenericTreeModel.__init__(self)

        # Callback for when the filter / list changes, gets one parameter
        # (has_episodes) that is True if the list has any episodes
        self._on_filter_changed = on_filter_changed

        self._downloading = lambda x: False
        self._include_description = False
        self._generate_thumbnails = False

        self._episodes = []

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = self.VIEW_ALL
        self._search_term = None
        self._filter.set_visible_func(self._filter_visible_func)

        # Are we currently showing the "all episodes" view?
        self._all_episodes_view = False

        # "ICON" is used to mark icon names in source files
        ICON = lambda x: x

        self._icon_cache = {}
        self.ICON_AUDIO_FILE = ICON('general_audio_file')
        self.ICON_VIDEO_FILE = ICON('general_video_file')
        self.ICON_IMAGE_FILE = ICON('general_image')
        self.ICON_GENERIC_FILE = ICON('filemanager_unknown_file')
        self.ICON_DOWNLOADING = ICON('email_inbox')
        self.ICON_DELETED = ICON('camera_delete')
        self.ICON_UNPLAYED = ICON('emblem-new')
        self.ICON_LOCKED = ICON('emblem-readonly')
        self.ICON_MISSING = ICON('emblem-unreadable')
        self.ICON_NEW = gtk.STOCK_ABOUT

        normal_font = style.get_font_desc('SystemFont')
        normal_color = style.get_color('DefaultTextColor')
        normal = (normal_font.to_string(), normal_color.to_string())
        self._normal_markup = '<span font_desc="%s" foreground="%s">%%s</span>' % normal

        active_font = style.get_font_desc('SystemFont')
        active_color = style.get_color('ActiveTextColor')
        active = (active_font.to_string(), active_color.to_string())
        self._active_markup = '<span font_desc="%s" foreground="%s">%%s</span>' % active

        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        sub = '\n<span font_desc="%s" foreground="%s">%%s</span>' % sub

        self._unplayed_markup = self._normal_markup + sub
        self._active_markup += sub



    def _format_filesize(self, episode):
        if episode.file_size > 0:
            return util.format_filesize(episode.file_size, 1)
        else:
            return None


    def _filter_visible_func(self, model, iter):
        # If searching is active, set visibility based on search text
        if self._search_term is not None:
            episode = model.get_value(iter, self.C_EPISODE)
            q = query.UserEQL(self._search_term)
            return q.match(episode)

        if self._view_mode == self.VIEW_ALL:
            return True
        elif self._view_mode == self.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNDELETED)
        elif self._view_mode == self.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VIEW_SHOW_DOWNLOADED)
        elif self._view_mode == self.VIEW_UNPLAYED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNPLAYED)

        return True

    def has_episodes(self):
        """Returns True if episodes are visible (filtered)

        If episodes are visible with the current filter
        applied, return True (otherwise return False).
        """

        if self._search_term is not None:
            is_visible = query.UserEQL(self._search_term).match
        elif self._view_mode == self.VIEW_ALL:
            return bool(self._episodes)
        elif self._view_mode == self.VIEW_UNDELETED:
            is_visible = lambda episode: episode.state != gpodder.STATE_DELETED or \
                    self._downloading(episode)
        elif self._view_mode == self.VIEW_DOWNLOADED:
            is_visible = lambda episode: episode.state == gpodder.STATE_DOWNLOADED or \
                    (episode.state == gpodder.STATE_NORMAL and \
                     not episode.is_played) or \
                    self._downloading(episode)
        elif self._view_mode == self.VIEW_UNPLAYED:
            is_visible = lambda episode: (not episode.is_played and (episode.state in \
                    (gpodder.STATE_DOWNLOADED, gpodder.STATE_NORMAL))) or \
                    self._downloading(episode)
        else:
            log('Should never reach this in has_episodes()!', sender=self)
            return True

        return any(is_visible(episode) for episode in self._episodes)

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


    def _format_description(self, episode):
        if self._downloading(episode):
            sub = _('in downloads list')
            if self._all_episodes_view:
                sub = '; '.join((sub, _('from %s') % cgi.escape(episode.channel.title,)))
            return self._unplayed_markup % (cgi.escape(episode.title), sub)
        elif episode.is_played:
            if self._all_episodes_view:
                sub = _('from %s') % cgi.escape(episode.channel.title,)
                return self._unplayed_markup % (cgi.escape(episode.title), sub)
            else:
                return self._normal_markup % (cgi.escape(episode.title),)
        else:
            if episode.was_downloaded(and_exists=True):
                sub = _('unplayed download')
            else:
                sub = _('new episode')

            if self._all_episodes_view:
                sub = '; '.join((sub, _('from %s') % cgi.escape(episode.channel.title,)))

            return self._active_markup % (cgi.escape(episode.title), sub)

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

        self._on_filter_changed(self.has_episodes())


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
                episode.reload_from_db()
                self.emit('row-changed', (index,), self.create_tree_iter(index))

    def update_by_filter_iter(self, iter, downloading=None, \
            include_description=False, generate_thumbnails=False):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
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



class PodcastListModel(model.PodcastListModel):
    def __init__(self, *args):
        model.PodcastListModel.__init__(self, *args)

        normal_font = style.get_font_desc('SystemFont')
        normal_color = style.get_color('DefaultTextColor')
        normal = (normal_font.to_string(), normal_color.to_string())
        self._normal_markup = '<span font_desc="%s" foreground="%s">%%s</span>' % normal

        active_font = style.get_font_desc('SystemFont')
        active_color = style.get_color('ActiveTextColor')
        active = (active_font.to_string(), active_color.to_string())
        self._active_markup = '<span font_desc="%s" foreground="%s">%%s</span>' % active

        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        sub = '\n<span font_desc="%s" foreground="%s">%%s</span>' % sub

        self._unplayed_markup = self._normal_markup + sub
        self._active_markup += sub

    def _format_description(self, channel, total, deleted, \
            new, downloaded, unplayed):
        title_markup = cgi.escape(channel.title)
        if channel.pause_subscription:
            disabled_text = cgi.escape(_('Subscription paused'))
            if new:
                return self._active_markup % (title_markup, disabled_text)
            else:
                return self._unplayed_markup % (title_markup, disabled_text)
        if not unplayed and not new:
            return self._normal_markup % title_markup

        new_text = N_('%(count)d new episode', '%(count)d new episodes', new) % {'count':new}
        unplayed_text = N_('%(count)d unplayed download', '%(count)d unplayed downloads', unplayed) % {'count':unplayed}
        if new and unplayed:
            return self._active_markup % (title_markup, ', '.join((new_text, unplayed_text)))
        elif new:
            return self._active_markup % (title_markup, new_text)
        elif unplayed:
            return self._unplayed_markup % (title_markup, unplayed_text)

