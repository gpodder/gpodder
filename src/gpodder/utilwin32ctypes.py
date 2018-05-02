# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
# Copyright (c) 2018 Eric Le Lay
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

import ctypes
from ctypes import c_ulonglong
from ctypes.wintypes import (BOOL, DWORD, LPCWSTR, PULARGE_INTEGER)

from  win32ctypes.core.ctypes._common import byreference
from  win32ctypes.core.ctypes._util import check_zero, function_factory

# Use a local copy of the kernel32 dll.
kernel32 = ctypes.WinDLL('kernel32')

_BaseGetDiskFreeSpaceEx = function_factory(
    kernel32.GetDiskFreeSpaceExW,
    [LPCWSTR, PULARGE_INTEGER, PULARGE_INTEGER, PULARGE_INTEGER],
    BOOL, check_zero)

_BaseGetFileAttributes = function_factory(
    kernel32.GetFileAttributesW,
    [LPCWSTR],
    DWORD)

def GetDiskFreeSpaceEx(lpDirectoryName):
    lp_dirname = LPCWSTR(lpDirectoryName)
    lpFreeBytesAvailable = c_ulonglong(0)
    lpTotalNumberOfBytes = c_ulonglong(0)
    lpTotalNumberOfFreeBytes = c_ulonglong(0)
    _BaseGetDiskFreeSpaceEx(lp_dirname, byreference(lpFreeBytesAvailable), byreference(lpTotalNumberOfBytes), byreference(lpTotalNumberOfFreeBytes))
    freeBytesAvailable = lpFreeBytesAvailable.value
    totalNumberOfBytes = lpTotalNumberOfBytes.value
    totalNumberOfFreeBytes = lpTotalNumberOfFreeBytes.value
    return (freeBytesAvailable, totalNumberOfBytes, totalNumberOfFreeBytes)

def GetFileAttributes(lpFileName):
    lp_filename = LPCWSTR(lpFileName)
    return _BaseGetFileAttributes(lp_filename)
