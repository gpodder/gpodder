# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

# Ubuntu Unity Launcher Integration
# Thomas Perl <thp@gpodder.org>; 2012-02-06

# FIXME: Due to the fact that we do not yet use the GI-style bindings, we will
# have to run this module in its own interpreter and send commands to it using
# the subprocess module. Once we use GI-style bindings, we can get rid of all
# this and still expose the same "interface' (LauncherEntry and its methods)
# to our callers.

import subprocess
import logging

if __name__ != '__main__':
    logger = logging.getLogger(__name__)

    class LauncherEntry:
        FILENAME = 'gpodder.desktop'

        def __init__(self):
            self.process = subprocess.Popen(['python', __file__],
                    stdin=subprocess.PIPE)

        def set_count(self, count):
            try:
                self.process.stdin.write('count %d\n' % count)
                self.process.stdin.flush()
            except Exception, e:
                logger.debug('Ubuntu count update failed.', exc_info=True)

        def set_progress(self, progress):
            try:
                self.process.stdin.write('progress %f\n' % progress)
                self.process.stdin.flush()
            except Exception, e:
                logger.debug('Ubuntu progress update failed.', exc_info=True)

if __name__ == '__main__':
    from gi.repository import Unity, GObject
    import threading
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
                    if command == 'count':
                        GObject.idle_add(launcher_entry.set_count, int(value))
                    elif command == 'progress':
                        GObject.idle_add(launcher_entry.set_progress, float(value))
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
    threading.Thread(target=loop.run).start()

    launcher_entry = LauncherEntry()
    reader = InputReader(sys.stdin, launcher_entry)
    reader.read()

    loop.quit()

