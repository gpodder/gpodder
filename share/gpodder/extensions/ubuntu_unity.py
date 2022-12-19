# -*- coding: utf-8 -*-

# Ubuntu Unity Launcher Integration
# Thomas Perl <thp@gpodder.org>; 2012-02-06

import logging

import gpodder

import gi  # isort:skip
gi.require_version('Unity', '7.0')  # isort:skip
from gi.repository import GLib, Unity  # isort:skip


_ = gpodder.gettext
logger = logging.getLogger(__name__)

__title__ = _('Ubuntu Unity Integration')
__description__ = _('Show download progress in the Unity Launcher icon.')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'desktop-integration'
__only_for__ = 'unity'
__mandatory_in__ = 'unity'
__disable_in__ = 'win32'


class LauncherEntry:
    FILENAME = 'gpodder.desktop'

    def __init__(self):
        self.launcher = Unity.LauncherEntry.get_for_desktop_id(
            self.FILENAME)

    def set_count(self, count):
        self.launcher.set_property('count', count)
        self.launcher.set_property('count_visible', count > 0)

    def set_progress(self, progress):
        self.launcher.set_property('progress', progress)
        self.launcher.set_property('progress_visible', 0. <= progress < 1.)


class gPodderExtension:
    FILENAME = 'gpodder.desktop'

    def __init__(self, container):
        self.container = container
        self.launcher_entry = None

    def on_load(self):
        logger.info('Starting Ubuntu Unity Integration.')
        self.launcher_entry = LauncherEntry()

    def on_unload(self):
        self.launcher_entry = None

    def on_download_progress(self, progress):
        GLib.idle_add(self.launcher_entry.set_progress, float(progress))
