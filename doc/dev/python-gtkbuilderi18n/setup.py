
#
# Very simple wrapper around bindtextdomain() from GNU gettext/libintl,
# because gtk.Builder uses the C library version of gettext and not Python's
# gettext. Under Linux, we can use the locale module to directly use the
# C library's bindtextdomain() function, but not so under Win32.
#
# Build with:
#    python setup.py build -cmingw32
#    python setup.py install
#
# (based on http://sebsauvage.net/python/mingw.html)
#

import distutils
from distutils.core import setup, Extension

setup(name='gtkbuilderi18n',
      description='gtk.Builder() i18n Support for Win32',
      version='1.0',
      ext_modules=[Extension('_gtkbuilderi18n',
	                     ['gtkbuilderi18n.c', 'gtkbuilderi18n.i'],
			     libraries=['intl'])])

