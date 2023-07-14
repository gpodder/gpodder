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
Current state (2018/07/29 ELL):
 - I can't get pywin32 to work in msys2 (the platform used for this python3/gtk3 installer)
   so existing code using COM doesn't work.
 - Gio.Notification is not implemented on windows yet.
   see https://bugzilla.gnome.org/show_bug.cgi?id=776583
 - Gtk.StatusIcon with a context works but is deprecated. Showing a balloon using set_tooltip_markup
   doesn't work.
   See https://github.com/afiskon/py-gtk-example
 - hexchat have implemented a solid c++ solution.
   See https://github.com/hexchat/hexchat/tree/master/src/fe-gtk/notifications
I've chosen to implement notifications by calling a PowerShell script invoking
Windows Toast Notification API or Balloon Notification as fallback.
It's tested on Win7 32bit and Win10 64bit VMs from modern.ie
So we have a working solution until Gio.Notification is implemented on Windows.
"""
import logging
import os
import os.path
import subprocess
import sys
import tempfile

import gpodder

logger = logging.getLogger(__name__)
_ = gpodder.gettext

__title__ = _('Notification Bubbles for Windows')
__description__ = _('Display notification bubbles for different events.')
__authors__ = 'Sean Munkel <SeanMunkel@gmail.com>'
__category__ = 'desktop-integration'
__mandatory_in__ = 'win32'
__only_for__ = 'win32'


class gPodderExtension(object):
    def __init__(self, *args):
        gpodder_script = sys.argv[0]
        gpodder_script = os.path.realpath(gpodder_script)
        self._icon = os.path.join(os.path.dirname(gpodder_script), "gpodder.ico")

    def on_notification_show(self, title, message):
        script = """
try {{
    if ([Environment]::OSVersion.Version -ge (new-object 'Version' 10,0,10240)) {{
        # use Windows 10 Toast notification
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        # Need a real AppID (see https://stackoverflow.com/q/46814858)
        # use gPodder app id if it's the installed, otherwise use PowerShell's AppID
        try {{
            $gpo_appid = Get-StartApps -Name "gpodder"
        }} catch {{
            write-host "Get-StartApps not available"
            $gpo_appid = $null
        }}
        if ($gpo_appid -ne $null) {{
            $APP_ID = $gpo_appid[0].AppID
        }} else {{
            $APP_ID = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
        }}
        $template = @"
<toast activationType="protocol" launch="" duration="long">
    <visual>
        <binding template="ToastGeneric">
            <image placement="appLogoOverride" src="{icon}" />
            <text><![CDATA[{title}]]></text>
            <text><![CDATA[{message}]]></text>
        </binding>
    </visual>
    <audio silent="true" />
</toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
        Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force    # Delete this script temp file.
    }} else {{
        # use older Balloon notification when not on Windows 10
        [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
        $o = New-Object System.Windows.Forms.NotifyIcon

        $o.Icon = "{icon}"
        $o.BalloonTipIcon = "None"
        $o.BalloonTipText = @"
{message}
"@
        $o.BalloonTipTitle = @"
{title}
"@

    $o.Visible = $True
    $Delay = 10    # Delay value in seconds.
    $o.ShowBalloonTip($Delay*1000)
    Start-Sleep -s $Delay
    $o.Dispose()
    Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force    # Delete this script temp file.
    }}
}} catch {{
    write-host "Caught an exception:"
    write-host "Exception Type: $($_.Exception.GetType().FullName)"
    write-host "Exception Message: $($_.Exception.Message)"
    exit 1
}}
""".format(icon=self._icon, message=message, title=title)
        fh, path = tempfile.mkstemp(suffix=".ps1")
        with open(fh, "w", encoding="utf_8_sig") as f:
            f.write(script)
        try:
            # hide powershell command window using startupinfo
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            # to run 64bit powershell on Win10 64bit when running from 32bit gPodder
            # (we need 64bit powershell on Win10 otherwise Get-StartApps is not available)
            powershell = r"{}\sysnative\WindowsPowerShell\v1.0\powershell.exe".format(os.environ["SystemRoot"])
            if not os.path.exists(powershell):
                powershell = "powershell.exe"
            subprocess.Popen([powershell,
                           "-ExecutionPolicy", "Bypass", "-File", path],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           startupinfo=startupinfo)
        except subprocess.CalledProcessError as e:
            logger.error("Error in on_notification_show(title=%r, message=%r):\n"
                         "\t%r exit code %i\n\tstdout=%s\n\tstderr=%s",
                         title, message, e.cmd, e.returncode, e.stdout, e.stderr)
        except FileNotFoundError:
            logger.error("Error in on_notification_show(title=%r, message=%r): %s not found",
                         title, message, powershell)

    def on_unload(self):
        pass
