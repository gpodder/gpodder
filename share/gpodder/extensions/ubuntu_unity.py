# -*- coding: utf-8 -*-

# Ubuntu Unity Launcher Integration
# Thomas Perl <thp@gpodder.org>; 2012-02-06

import gpodder

_ = gpodder.gettext

__title__ = _('Ubuntu Unity Integration')
__description__ = _('Show download progress in the Unity Launcher icon.')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'desktop-integration'
__only_for__ = 'unity'
__mandatory_in__ = 'unity'
__disable_in__ = 'win32'


# FIXME: Due to the fact that we do not yet use the GI-style bindings, we will
# have to run this module in its own interpreter and send commands to it using
# the subprocess module. Once we use GI-style bindings, we can get rid of all
# this and still expose the same "interface' (LauncherEntry and its methods)
# to our callers.

import os
import subprocess
import sys
import logging

if __name__ != '__main__':
    logger = logging.getLogger(__name__)

    class gPodderExtension:
        FILENAME = 'gpodder.desktop'

        def __init__(self, container):
            self.container = container
            self.process = None

        def on_load(self):
            logger.info('Starting Ubuntu Unity Integration.')
            os.environ['PYTHONPATH'] = os.pathsep.join(sys.path)
            self.process = subprocess.Popen(['python', __file__],
                    stdin=subprocess.PIPE)

        def on_unload(self):
            logger.info('Killing process...')
            self.process.terminate()
            self.process.wait()
            logger.info('Process killed.')

        def on_download_progress(self, progress):
            try:
                self.process.stdin.write('progress %f\n' % progress)
                self.process.stdin.flush()
            except Exception, e:
                logger.debug('Ubuntu progress update failed.', exc_info=True)
else:
    from gi.repository import Unity, GObject
    from gpodder import util
    import sys

    class InputReader:
        def __init__(self, fileobj, launcher):
            self.fileobj = fileobj
            self.launcher = launcher

        def read(self):
            while True:
                line = self.fileobj.readline()
                if not line:
                    break

                try:
                    command, value = line.strip().split()
                    if command == 'progress':
                        GObject.idle_add(launcher_entry.set_progress,
                                float(value))
                except:
                    pass

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

    GObject.threads_init()
    loop = GObject.MainLoop()
    util.run_in_background(loop.run)

    launcher_entry = LauncherEntry()
    reader = InputReader(sys.stdin, launcher_entry)
    reader.read()

    loop.quit()

