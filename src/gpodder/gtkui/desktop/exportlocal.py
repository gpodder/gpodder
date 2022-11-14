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
import os

import gpodder
from gpodder.gtkui.interface.common import BuilderWidget

_ = gpodder.gettext
N_ = gpodder.ngettext


class gPodderExportToLocalFolder(BuilderWidget):
    """ Export to Local Folder UI: file dialog + checkbox to save all to same folder """
    def new(self):
        self.gPodderExportToLocalFolder.set_transient_for(self.parent_widget)
        self.RES_CANCEL = -6
        self.RES_SAVE = -3
        self.gPodderExportToLocalFolder.add_buttons("_Cancel", self.RES_CANCEL,
                                                    "_Save", self.RES_SAVE)
        self._config.connect_gtk_window(self.gPodderExportToLocalFolder,
                                        'export_to_local_folder', True)

    def save_as(self, initial_directory, filename, remaining=0):
        """
        blocking method: prompt for save to local folder
        :param str initial_directory: folder to show to user or None
        :param str filename: default export filename
        :param int remaining: remaining episodes (to show/hide and customize checkbox label)
        :return (bool, str, str, bool): notCancelled, selected folder, selected path,
                                        save all remaining episodes with default params
        """
        if remaining:
            self.allsamefolder.set_label(
                N_('Export remaining %(count)d episode to this folder with its default name',
                   'Export remaining %(count)d episodes to this folder with their default name',
                   remaining) % {'count': remaining})
        else:
            self.allsamefolder.hide()
        if initial_directory is None:
            initial_directory = os.path.expanduser('~')
        self.gPodderExportToLocalFolder.set_current_folder(initial_directory)
        self.gPodderExportToLocalFolder.set_current_name(filename)
        res = self.gPodderExportToLocalFolder.run()
        self.gPodderExportToLocalFolder.hide()
        notCancelled = (res == self.RES_SAVE)
        allRemainingDefault = self.allsamefolder.get_active()
        if notCancelled:
            folder = self.gPodderExportToLocalFolder.get_current_folder()
            filename = self.gPodderExportToLocalFolder.get_filename()
        else:
            folder = initial_directory
            filename = None
        return (notCancelled, folder, filename, allRemainingDefault)
