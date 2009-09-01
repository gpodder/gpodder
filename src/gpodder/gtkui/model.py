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
#  gpodder.gtkui.model - GUI model classes for gPodder (2009-08-13)
#  Based on code from libpodcasts.py (thp, 2005-10-29)
#

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui import draw

import gtk
import xml.sax.saxutils


class EpisodeListModel(gtk.ListStore):
    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
            C_PUBLISHED_TEXT, C_DESCRIPTION, C_DESCRIPTION_STRIPPED, \
            C_IS_NOT_DELETED, C_IS_DOWNLOADED_NEW_DLING = range(10)

    VIEW_ALL, VIEW_UNDELETED, VIEW_DOWNLOADED = range(3)

    def __init__(self):
        gtk.ListStore.__init__(self, str, str, str, object, \
                gtk.gdk.Pixbuf, str, str, str, bool, bool)

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = self.VIEW_ALL
        self._filter.set_visible_func(self._filter_visible_func)

        self._icon_cache = {}
        if gpodder.interface == gpodder.MAEMO:
            self.ICON_AUDIO_FILE = 'gnome-mime-audio-mp3'
            self.ICON_VIDEO_FILE = 'gnome-mime-video-mp4'
            self.ICON_GENERIC_FILE = 'text-x-generic'
            self.ICON_DOWNLOADING = 'qgn_toolb_messagin_moveto'
            self.ICON_DELETED = 'qgn_toolb_gene_deletebutton'
            self.ICON_NEW = 'qgn_list_gene_favor'
            self.ICON_UNPLAYED = 'qgn_list_gene_favor'
            self.ICON_LOCKED = 'qgn_indi_KeypadLk_lock'
            self.ICON_MISSING = gtk.STOCK_STOP # FIXME!
        else:
            self.ICON_AUDIO_FILE = 'audio-x-generic'
            self.ICON_VIDEO_FILE = 'video-x-generic'
            self.ICON_GENERIC_FILE = 'text-x-generic'
            self.ICON_DOWNLOADING = gtk.STOCK_GO_DOWN
            self.ICON_DELETED = gtk.STOCK_DELETE
            self.ICON_NEW = gtk.STOCK_ABOUT
            self.ICON_UNPLAYED = 'emblem-new'
            self.ICON_LOCKED = 'emblem-readonly'
            self.ICON_MISSING = 'emblem-unreadable'


    def _format_filesize(self, episode):
        if episode.length > 0:
            return util.format_filesize(episode.length, 1)
        else:
            return None


    def _filter_visible_func(self, model, iter):
        if self._view_mode == self.VIEW_ALL:
            return True
        elif self._view_mode == self.VIEW_UNDELETED:
            return model.get_value(iter, self.C_IS_NOT_DELETED)
        elif self._view_mode == self.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_IS_DOWNLOADED_NEW_DLING)

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


    def update_from_channel(self, channel, downloading=None, \
            include_description=False, finish_callback=None):
        """
        Return a gtk.ListStore containing episodes for the given channel.
        Downloading should be a callback.
        include_description should be a boolean value (True if description
        is to be added to the episode row, or False if not)
        """
        self.clear()
        for episode in channel.get_all_episodes():
            description = episode.format_episode_row_markup(include_description)
            description_stripped = util.remove_html_tags(episode.description)

            iter = self.append()
            self.set(iter, \
                    self.C_URL, episode.url, \
                    self.C_TITLE, episode.title, \
                    self.C_FILESIZE_TEXT, self._format_filesize(episode), \
                    self.C_EPISODE, episode, \
                    self.C_PUBLISHED_TEXT, episode.cute_pubdate(), \
                    self.C_DESCRIPTION, description, \
                    self.C_DESCRIPTION_STRIPPED, description_stripped)

            self.update_by_iter(iter, downloading, include_description)

        if finish_callback is not None:
            finish_callback()

    def update_by_urls(self, urls, downloading=None, include_description=False):
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter, downloading, include_description)

    def update_by_filter_iter(self, iter, downloading=None, \
            include_description=False):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter), \
                downloading, include_description)

    def update_by_iter(self, iter, downloading=None, include_description=False):
        episode = self.get_value(iter, self.C_EPISODE)
        episode.reload_from_db()

        if include_description:
            icon_size = 32
        else:
            icon_size = 16

        show_bullet = False
        show_padlock = False
        show_missing = False
        status_icon = None
        deleted = False
        downloaded_new_downloading = False

        if downloading is not None and downloading(episode):
            status_icon = self.ICON_DOWNLOADING
            downloaded_new_downloading = True
        else:
            if episode.state == gpodder.STATE_DELETED:
                status_icon = self.ICON_DELETED
                deleted = True
            elif episode.state == gpodder.STATE_NORMAL and \
                    not episode.is_played:
                status_icon = self.ICON_NEW
                downloaded_new_downloading = True
            elif episode.state == gpodder.STATE_DOWNLOADED:
                downloaded_new_downloading = True
                show_bullet = not episode.is_played
                show_padlock = episode.is_locked
                show_missing = not episode.file_exists()

                file_type = episode.file_type()
                if file_type == 'audio':
                    status_icon = self.ICON_AUDIO_FILE
                elif file_type == 'video':
                    status_icon = self.ICON_VIDEO_FILE
                else:
                    status_icon = self.ICON_GENERIC_FILE

        if status_icon is not None:
            status_icon = self._get_tree_icon(status_icon, show_bullet, \
                    show_padlock, show_missing, icon_size)

        self.set(iter, \
                self.C_STATUS_ICON, status_icon, \
                self.C_IS_NOT_DELETED, not deleted, \
                self.C_IS_DOWNLOADED_NEW_DLING, downloaded_new_downloading)

    def _get_tree_icon(self, icon_name, add_bullet=False, \
            add_padlock=False, add_missing=False, icon_size=32):
        """
        Loads an icon from the current icon theme at the specified
        size, suitable for display in a gtk.TreeView. Additional
        emblems can be added on top of the icon.
        """

        if (icon_name,add_bullet,add_padlock,icon_size) in self._icon_cache:
            return self._icon_cache[(icon_name,add_bullet,add_padlock,icon_size)]

        icon_theme = gtk.icon_theme_get_default()

        try:
            icon = icon_theme.load_icon(icon_name, icon_size, 0)
        except:
            icon = icon_theme.load_icon(gtk.STOCK_DIALOG_QUESTION, icon_size, 0)

        if icon and (add_bullet or add_padlock or add_missing):
            # We'll modify the icon, so use .copy()
            if add_missing:
                try:
                    icon = icon.copy()
                    emblem = icon_theme.load_icon(self.ICON_MISSING, int(float(icon_size)*1.2/3.0), 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    xpos = icon.get_width() - width
                    ypos = icon.get_height() - height
                    emblem.composite(icon, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass
            elif add_bullet:
                try:
                    icon = icon.copy()
                    emblem = icon_theme.load_icon(self.ICON_UNPLAYED, int(float(icon_size)*1.2/3.0), 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    xpos = icon.get_width() - width
                    ypos = icon.get_height() - height
                    emblem.composite(icon, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass
            if add_padlock:
                try:
                    icon = icon.copy()
                    emblem = icon_theme.load_icon(self.ICON_LOCKED, int(float(icon_size)/2.0), 0)
                    (width, height) = (emblem.get_width(), emblem.get_height())
                    emblem.composite(icon, 0, 0, width, height, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
                except:
                    pass

        self._icon_cache[(icon_name,add_bullet,add_padlock,icon_size)] = icon
        return icon


class PodcastListModel(gtk.ListStore):
    C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL, \
            C_COVER, C_ERROR, C_PILL_VISIBLE, \
            C_VISIBLE_UNDELETED, C_VISIBLE_DOWNLOADED = range(10)

    def __init__(self, max_image_side, cover_downloader):
        gtk.ListStore.__init__(self, str, str, str, gtk.gdk.Pixbuf, \
                object, gtk.gdk.Pixbuf, str, bool, bool, bool)

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = EpisodeListModel.VIEW_ALL
        self._filter.set_visible_func(self._filter_visible_func)

        self._cover_cache = {}
        self._max_image_side = max_image_side
        self._cover_downloader = cover_downloader


    def _filter_visible_func(self, model, iter):
        if self._view_mode == EpisodeListModel.VIEW_ALL:
            return True
        elif self._view_mode == EpisodeListModel.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VISIBLE_UNDELETED)
        elif self._view_mode == EpisodeListModel.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VISIBLE_DOWNLOADED)

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

    def _get_cover_image(self, channel):
        if self._cover_downloader is None:
            return None

        pixbuf = self._cover_downloader.get_cover(channel, avoid_downloading=True)
        return self._resize_pixbuf(channel.url, pixbuf)

    def _get_pill_image(self, channel, count_downloaded, count_unplayed):
        if count_unplayed > 0 or count_downloaded > 0:
            return draw.draw_pill_pixbuf(str(count_unplayed), str(count_downloaded))
        else:
            return None

    def _format_description(self, channel, count_new):
        title_markup = xml.sax.saxutils.escape(channel.title)
        description_markup = xml.sax.saxutils.escape(util.get_first_line(channel.description) or ' ')
        d = []
        if count_new:
            d.append('<span weight="bold">')
        d.append(title_markup)
        if count_new:
            d.append('</span>')
        return ''.join(d+['\n', '<small>', description_markup, '</small>'])

    def _format_error(self, channel):
        if channel.parse_error:
            return str(channel.parse_error)
        else:
            return None

    def set_channels(self, channels):
        # Clear the model and update the list of podcasts
        self.clear()
        for channel in channels:
            iter = self.append()
            self.set(iter, \
                    self.C_URL, channel.url, \
                    self.C_CHANNEL, channel, \
                    self.C_COVER, self._get_cover_image(channel))
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

    def update_by_urls(self, urls):
        # Given a list of URLs, update each matching row
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter)

    def update_by_filter_iter(self, iter):
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def update_by_iter(self, iter):
        # Given a GtkTreeIter, update volatile information
        channel = self.get_value(iter, self.C_CHANNEL)
        total, deleted, new, downloaded, unplayed = channel.get_statistics()

        pill_image = self._get_pill_image(channel, downloaded, unplayed)
        self.set(iter, \
                self.C_TITLE, channel.title, \
                self.C_DESCRIPTION, self._format_description(channel, new), \
                self.C_ERROR, self._format_error(channel), \
                self.C_PILL, pill_image, \
                self.C_PILL_VISIBLE, pill_image != None, \
                self.C_VISIBLE_UNDELETED, total > deleted, \
                self.C_VISIBLE_DOWNLOADED, downloaded + new > 0)

    def add_cover_by_url(self, url, pixbuf):
        # Resize and add the new cover image
        pixbuf = self._resize_pixbuf(url, pixbuf)
        for row in self:
            if row[self.C_URL] == url:
                row[self.C_COVER] = pixbuf
                break

    def delete_cover_by_url(self, url):
        # Remove the cover from the model
        for row in self:
            if row[self.C_URL] == url:
                row[self.C_COVER] = None
                break

        # Remove the cover from the cache
        key = (url, self._max_image_side, self._max_image_side)
        if key in self._cover_cache:
            del self._cover_cache[key]

