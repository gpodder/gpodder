# -*- coding: utf-8 -*-

# Minimize gPodder's main window on startup
# Thomas Perl <thp@gpodder.org>; 2012-07-31

import gpodder

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
            ui_object.main_window.iconify()

