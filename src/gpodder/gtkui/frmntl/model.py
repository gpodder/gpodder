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

from gpodder.gtkui import download
from gpodder.gtkui import model
from gpodder.gtkui.frmntl import style

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


class EpisodeListModel(model.EpisodeListModel):
    def __init__(self):
        model.EpisodeListModel.__init__(self)

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

    def _format_description(self, episode, include_description=False, is_downloading=None):
        if is_downloading is not None and is_downloading(episode):
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
        if not unplayed and not new:
            return self._normal_markup % title_markup

        new_text = N_('%d new episode', '%d new episodes', new) % new
        unplayed_text = N_('%d unplayed download', '%d unplayed downloads', unplayed) % unplayed
        if new and unplayed:
            return self._active_markup % (title_markup, ', '.join((new_text, unplayed_text)))
        elif new:
            return self._active_markup % (title_markup, new_text)
        elif unplayed:
            return self._unplayed_markup % (title_markup, unplayed_text)

