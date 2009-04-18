#!/usr/bin/python
""" Generates a mediawiki-compatible table of all the gPodder settings

    Usage: doc/config-doc-generator.py > some-file.txt
    Fancy usage: LANG=fr_FR.UTF-8 PYTHONPATH=src/ LOCALEDIR=data/locale/ \
                 doc/config-doc-generator.py > some-file.txt

    Poke nikosapi <me@nikosapi.org> if this doesn't work
"""

import os, os.path
import gettext

# Enable i18n support
domain = 'gpodder'
locale_dir = os.environ.get('LOCALEDIR', '/usr/share/locale/')
locale_dir = os.path.abspath( os.path.normpath( locale_dir ))
gettext.bindtextdomain( domain, locale_dir)
gettext.textdomain( domain)
gettext.install(domain, locale_dir, unicode=True)

from gpodder import config

print '{| border="1" cellpadding="2"'
for i in [ 'Name', 'Type', 'Default', 'Description' ]:
    print "!", i

settings = config.gPodderSettings.keys()
settings.sort()

for setting in settings:
    data = config.gPodderSettings[setting]
    if len(data) == 2:
        dtype, default = data
        desc = 'FIXME: Undocumented'
    elif len(data) == 3:
        dtype, default, desc = data
    else:
        continue

    if dtype == str and default == '':
        default = '<i>empty string</i>'

    dtype = dtype.__name__

    if setting == 'download_dir':
        default = default.replace( os.path.expanduser('~'), '~' )

    print '|-'
    print '|%s || %s || %s || %s' % (setting, dtype, default, desc)

print '|}'

