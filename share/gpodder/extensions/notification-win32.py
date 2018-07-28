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

# Notification implementation for Windows
# Sean Munkel; 2012-12-29
"""
Notification implementation for Windows.
Current state (2018/05/01 ELL):
 - I can't get pywin32 to work in msys2 (the platform used for this python3/gtk3 installer)
   so existing code using COM doesn't work.
 - Gio.Notification is not implemented on windows yet.
   see https://bugzilla.gnome.org/show_bug.cgi?id=776583
 - Gtk.StatusIcon with a context works but is deprecated. Showing a balloon using set_tooltip_markup
   doesn't work.
   See https://github.com/afiskon/py-gtk-example
 - in-app notifications using an overlay are pleasing to the eye, but don't solve the problem
   see https://stackoverflow.com/questions/45431512/gtk-in-app-notifications-api-referece
 - hexchat have implemented a solid c++ solution.
   See https://github.com/hexchat/hexchat/tree/master/src/fe-gtk/notifications
I've chosen to implement a cheap workaround using gtk.MessageDialog because
Gio.Notification will likely be implemented in 6 months-1 year
"""
__title__ = 'Notification Bubbles for Windows'
__description__ = 'Display notification bubbles for different events.'
__authors__ = 'Sean Munkel <SeanMunkel@gmail.com>'
__category__ = 'desktop-integration'
__mandatory_in__ = 'win32'
__only_for__ = 'win32'

import os
import os.path
import subprocess
import sys
import tempfile

import gpodder

import logging

logger = logging.getLogger(__name__)


class gPodderExtension(object):
    def __init__(self, *args):
        gpodder_script = sys.argv[0]
        gpodder_script = os.path.realpath(gpodder_script)
        self._icon = os.path.join(os.path.dirname(gpodder_script), "gpodder.ico")

    def on_notification_show(self, title, message):
        script = """
try {
    [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
    $o = New-Object System.Windows.Forms.NotifyIcon

    $o.Icon = "%s"
    $o.BalloonTipIcon = "None"
    $o.BalloonTipText = @"
%s
"@
    $o.BalloonTipTitle = @"
%s
"@

    $o.Visible = $True
    $o.ShowBalloonTip(10000)
} catch {
    write-host "Caught an exception:"
    write-host "Exception Type: $($_.Exception.GetType().FullName)"
    write-host "Exception Message: $($_.Exception.Message)"
    exit 1
}
""" % (self._icon, message, title)
        fh, path = tempfile.mkstemp(suffix=".ps1")
        with open(fh, "w", encoding="utf_8_sig") as f:
            f.write(script)
        try:
            subprocess.run(["powershell.exe", "-windowstyle", "hidden",  "-NoLogo", path], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            os.remove(path)  # XXX: otherwise keep it for debugging
        except subprocess.CalledProcessError as e:
            logger.error("Error in on_notification_show(title=%r, message=%r):\n"
                         "\t%r exit code %i\n\tstdout=%s\n\tstderr=%s",
                         title, message, e.cmd, e.returncode, e.stdout, e.stderr)

    def on_unload(self):
        pass
