# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

# Windows 7 taskbar progress
# Sean Munkel; 2013-01-05

import gpodder

_ = gpodder.gettext


__title__ = _('Show download progress on the taskbar')
__description__ = _('Displays the progress on the Windows taskbar.')
__authors__ = 'Sean Munkel <seanmunkel@gmail.com>'
__category__ = 'desktop-integration'
__only_for__ = 'win32'


from ctypes import (c_ushort, c_int, c_uint, c_ulong, c_ulonglong,
                    c_wchar_p, alignment, sizeof, Structure, POINTER)
from comtypes import IUnknown, GUID, COMMETHOD, wireHWND, client
from ctypes import HRESULT
from ctypes.wintypes import tagRECT
import functools

import logging
logger = logging.getLogger(__name__)

WSTRING = c_wchar_p
# values for enumeration 'TBPFLAG'
TBPF_NOPROGRESS = 0
TBPF_INDETERMINATE = 1
TBPF_NORMAL = 2
TBPF_ERROR = 4
TBPF_PAUSED = 8
TBPFLAG = c_int  # enum
# values for enumeration 'TBATFLAG'
TBATF_USEMDITHUMBNAIL = 1
TBATF_USEMDILIVEPREVIEW = 2
TBATFLAG = c_int  # enum


class tagTHUMBBUTTON(Structure):
    _fields_ = [
        ('dwMask', c_ulong),
        ('iId', c_uint),
        ('iBitmap', c_uint),
        ('hIcon', POINTER(IUnknown)),
        ('szTip', c_ushort * 260),
        ('dwFlags', c_ulong)]


class ITaskbarList(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{56FDF342-FD6D-11D0-958A-006097C9A090}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'HrInit'),
        COMMETHOD([], HRESULT, 'AddTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'DeleteTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'ActivateTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'SetActivateAlt',
                  (['in'], c_int, 'hwnd'))]


class ITaskbarList2(ITaskbarList):
    _case_insensitive_ = True
    _iid_ = GUID('{602D4995-B13A-429B-A66E-1935E44F4317}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'MarkFullscreenWindow',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_int, 'fFullscreen'))]


class ITaskbarList3(ITaskbarList2):
    _case_insensitive_ = True
    _iid_ = GUID('{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'SetProgressValue',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_ulonglong, 'ullCompleted'),
                  (['in'], c_ulonglong, 'ullTotal')),
        COMMETHOD([], HRESULT, 'SetProgressState',
                  (['in'], c_int, 'hwnd'),
                  (['in'], TBPFLAG, 'tbpFlags')),
        COMMETHOD([], HRESULT, 'RegisterTab',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], wireHWND, 'hwndMDI')),
        COMMETHOD([], HRESULT, 'UnregisterTab',
                  (['in'], c_int, 'hwndTab')),
        COMMETHOD([], HRESULT, 'SetTabOrder',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], c_int, 'hwndInsertBefore')),
        COMMETHOD([], HRESULT, 'SetTabActive',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], c_int, 'hwndMDI'),
                  (['in'], TBATFLAG, 'tbatFlags')),
        COMMETHOD([], HRESULT, 'ThumbBarAddButtons',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_uint, 'cButtons'),
                  (['in'], POINTER(tagTHUMBBUTTON), 'pButton')),
        COMMETHOD([], HRESULT, 'ThumbBarUpdateButtons',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_uint, 'cButtons'),
                  (['in'], POINTER(tagTHUMBBUTTON), 'pButton')),
        COMMETHOD([], HRESULT, 'ThumbBarSetImageList',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(IUnknown), 'himl')),
        COMMETHOD([], HRESULT, 'SetOverlayIcon',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(IUnknown), 'hIcon'),
                  (['in'], WSTRING, 'pszDescription')),
        COMMETHOD([], HRESULT, 'SetThumbnailTooltip',
                  (['in'], c_int, 'hwnd'),
                  (['in'], WSTRING, 'pszTip')),
        COMMETHOD([], HRESULT, 'SetThumbnailClip',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(tagRECT), 'prcClip'))]


assert sizeof(tagTHUMBBUTTON) == 540, sizeof(tagTHUMBBUTTON)
assert alignment(tagTHUMBBUTTON) == 4, alignment(tagTHUMBBUTTON)


# based on http://stackoverflow.com/a/1744503/905256
class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.window_handle = None
        self.restart_warning = True

    def on_load(self):
        self.taskbar = client.CreateObject(
                '{56FDF344-FD6D-11d0-958A-006097C9A090}',
                interface=ITaskbarList3)
        self.taskbar.HrInit()

    def on_unload(self):
        if self.taskbar is not None:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NOPROGRESS)

    def on_ui_object_available(self, name, ui_object):
        def callback(self, window, *args):
            self.window_handle = window.window.handle

        if name == 'gpodder-gtk':
            ui_object.main_window.connect('realize',
                    functools.partial(callback, self))

    def on_download_progress(self, progress):
        if self.window_handle is None:
            if not self.restart_warning:
                return
            logger.warn("No window handle available, a restart max fix this")
            self.restart_warning = False
            return
        if 0 < progress < 1:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NORMAL)
            self.taskbar.SetProgressValue(self.window_handle,
                    int(progress * 100), 100)
        else:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NOPROGRESS)

