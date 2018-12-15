# -*- coding: utf-8 -*-

# Minimize gPodder's main window on startup
# Thomas Perl <thp@gpodder.org>; 2012-07-31

import gpodder
from gpodder import util

_ = gpodder.gettext

__title__ = _('Minimize on start')
__description__ = _('Minimizes the gPodder window on startup.')
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.ui_object = ui_object

    def on_application_started(self):
        if self.ui_object:
            self.ui_object.main_window.iconify()
            util.idle_add(self.ui_object.main_window.iconify)
