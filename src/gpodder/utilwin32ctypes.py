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
from ctypes import HRESULT, Structure, byref, c_ulonglong
from ctypes.wintypes import (BOOL, BYTE, DWORD, HANDLE, LPCWSTR,
                             PULARGE_INTEGER, WORD)
from uuid import UUID

from win32ctypes.core.ctypes._util import check_zero, function_factory

# Use a local copy of dlls.
kernel32 = ctypes.WinDLL('kernel32')
shell32 = ctypes.WinDLL('shell32')
ole32 = ctypes.WinDLL('ole32')


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa373931%28v=vs.85%29.aspx
class GUID(ctypes.Structure):

    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", BYTE * 8),
    ]

    def __init__(self, uuidstr=None):
        uuid = UUID(uuidstr)
        Structure.__init__(self)
        self.Data1, self.Data2, self.Data3, self.Data4[0], self.Data4[1], rest = uuid.fields
        for i in range(2, 8):
            self.Data4[i] = rest >> (8 - i - 1) * 8 & 0xff


REFKNOWNFOLDERID = ctypes.POINTER(GUID)


S_OK = HRESULT(0).value

CoTaskMemFree = function_factory(
    ole32.CoTaskMemFree,
    [ctypes.c_void_p],
    None)


_BaseGetDiskFreeSpaceEx = function_factory(
    kernel32.GetDiskFreeSpaceExW,
    [LPCWSTR, PULARGE_INTEGER, PULARGE_INTEGER, PULARGE_INTEGER],
    BOOL, check_zero)


_BaseGetFileAttributes = function_factory(
    kernel32.GetFileAttributesW,
    [LPCWSTR],
    DWORD)


_BaseSHGetKnownFolderPath = function_factory(
    shell32.SHGetKnownFolderPath,
    [REFKNOWNFOLDERID, DWORD, HANDLE, ctypes.POINTER(ctypes.c_wchar_p)],
    HRESULT)


def GetDiskFreeSpaceEx(lpDirectoryName):
    lp_dirname = LPCWSTR(lpDirectoryName)
    lpFreeBytesAvailable = c_ulonglong(0)
    lpTotalNumberOfBytes = c_ulonglong(0)
    lpTotalNumberOfFreeBytes = c_ulonglong(0)
    _BaseGetDiskFreeSpaceEx(lp_dirname, byref(lpFreeBytesAvailable), byref(lpTotalNumberOfBytes), byref(lpTotalNumberOfFreeBytes))
    freeBytesAvailable = lpFreeBytesAvailable.value
    totalNumberOfBytes = lpTotalNumberOfBytes.value
    totalNumberOfFreeBytes = lpTotalNumberOfFreeBytes.value
    return (freeBytesAvailable, totalNumberOfBytes, totalNumberOfFreeBytes)


def GetFileAttributes(lpFileName):
    lp_filename = LPCWSTR(lpFileName)
    return _BaseGetFileAttributes(lp_filename)


def SHGetKnownFolderPath(rfid, dwFlags):
    out_buf = ctypes.c_wchar_p()
    try:
        ret = _BaseSHGetKnownFolderPath(byref(rfid), dwFlags, None, byref(out_buf))
    except WindowsError:
        return None
    if ret != S_OK:
        return None
    res = out_buf.value
    CoTaskMemFree(out_buf)
    return res


# https://msdn.microsoft.com/en-us/library/dd378447(v=vs.85).aspx
class KNOWN_FOLDER_FLAG:
    KF_FLAG_DEFAULT = 0x00000000
    KF_FLAG_SIMPLE_IDLIST = 0x00000100
    KF_FLAG_NOT_PARENT_RELATIVE = 0x00000200
    KF_FLAG_DEFAULT_PATH = 0x00000400
    KF_FLAG_INIT = 0x00000800
    KF_FLAG_NO_ALIAS = 0x00001000
    KF_FLAG_DONT_UNEXPAND = 0x00002000
    KF_FLAG_DONT_VERIFY = 0x00004000
    KF_FLAG_CREATE = 0x00008000
    KF_FLAG_NO_PACKAGE_REDIRECTION = 0x00010000
    KF_FLAG_NO_APPCONTAINER_REDIRECTION = 0x00010000
    KF_FLAG_FORCE_PACKAGE_REDIRECTION = 0x00020000
    KF_FLAG_FORCE_APPCONTAINER_REDIRECTION = 0x00020000
    KF_FLAG_RETURN_FILTER_REDIRECTION_TARGET = 0x00040000
    KF_FLAG_FORCE_APP_DATA_REDIRECTION = 0x00080000
    KF_FLAG_ALIAS_ONLY = 0x80000000


# https://msdn.microsoft.com/en-us/library/dd378457(v=vs.85).aspx
class KNOWNFOLDERID:
    FOLDERID_Documents = GUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")


def get_documents_folder():
    flags = KNOWN_FOLDER_FLAG.KF_FLAG_DEFAULT | \
                KNOWN_FOLDER_FLAG.KF_FLAG_DONT_UNEXPAND | \
                KNOWN_FOLDER_FLAG.KF_FLAG_CREATE | \
                KNOWN_FOLDER_FLAG.KF_FLAG_DONT_VERIFY
    return SHGetKnownFolderPath(KNOWNFOLDERID.FOLDERID_Documents, flags)


def get_reg_current_user_string_value(subkey, value_name):
    import winreg
    try:
        my_key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, subkey)
    except FileNotFoundError:
        return None
    try:
        value, type_ = winreg.QueryValueEx(my_key, value_name)
        if type_ == winreg.REG_SZ:
            return value
        else:
            raise WindowsError("Unexpected type for value %s in registry: %i" % (valueName, type_))
    except FileNotFoundError:
        return None
