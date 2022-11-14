# -*- coding: utf-8 -*-
# Concatenate multiple videos to a single file using ffmpeg
# 2014-05-03 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import logging
import os

from gi.repository import Gtk

import gpodder
from gpodder import util
from gpodder.gtkui.interface.progress import ProgressIndicator

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Concatenate videos')
__description__ = _('Add a context menu item for concatenating multiple videos')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.gpodder = None
        self.have_ffmpeg = (util.find_command('ffmpeg') is not None)

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def _get_save_filename(self):
        dlg = Gtk.FileChooserDialog(title=_('Save video'),
                parent=self.gpodder.get_dialog_parent(),
                action=Gtk.FileChooserAction.SAVE)
        dlg.add_button(_('_Cancel'), Gtk.ResponseType.CANCEL)
        dlg.add_button(_('_Save'), Gtk.ResponseType.OK)

        if dlg.run() == Gtk.ResponseType.OK:
            filename = dlg.get_filename()
            dlg.destroy()
            return filename

        dlg.destroy()

    def _concatenate_videos(self, episodes):
        episodes = self._get_sorted_episode_list(episodes)

        # TODO: Show file list dialog for reordering

        out_filename = self._get_save_filename()
        if out_filename is None:
            return

        list_filename = os.path.join(os.path.dirname(out_filename),
                '.' + os.path.splitext(os.path.basename(out_filename))[0] + '.txt')

        with open(list_filename, 'w') as fp:
            fp.write('\n'.join("file '%s'\n" % episode.local_filename(create=False)
                for episode in episodes))

        indicator = ProgressIndicator(_('Concatenating video files'),
                                      _('Writing %(filename)s') % {
                                          'filename': os.path.basename(out_filename)},
                                      False, self.gpodder.get_dialog_parent())

        def convert():
            ffmpeg = util.Popen(['ffmpeg', '-f', 'concat', '-nostdin', '-y',
                                 '-i', list_filename, '-c', 'copy', out_filename],
                                close_fds=True)
            result = ffmpeg.wait()
            util.delete_file(list_filename)

            indicator.on_finished()

            util.idle_add(lambda: self.gpodder.show_message(
                _('Videos successfully converted') if result == 0 else
                _('Error converting videos'),
                _('Concatenation result'), important=True))

        util.run_in_background(convert, True)

    def _is_downloaded_video(self, episode):
        return episode.file_exists() and episode.file_type() == 'video'

    def _get_sorted_episode_list(self, episodes):
        return sorted([e for e in episodes if self._is_downloaded_video(e)],
                key=lambda e: e.published)

    def on_episodes_context_menu(self, episodes):
        if self.gpodder is None or not self.have_ffmpeg:
            return None

        episodes = self._get_sorted_episode_list(episodes)

        if len(episodes) < 2:
            return None

        return [(_('Concatenate videos'), self._concatenate_videos)]
