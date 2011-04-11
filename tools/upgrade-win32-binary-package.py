#!/usr/bin/python
# Upgrade script for the gPodder Win32 release
# Injects new data into an old win32 release to build a new release
# Thomas Perl <thp.io/about>; 2011-04-08

# Required files:
# - An old win32 release
# - The source tarball of the new release
# - The (binary) Debian package of the new release
# - The source tarball of the most recent mygpoclient
# - The source tarball of the most recent feedparser

import os
import subprocess
import sys
import re
import glob

if len(sys.argv) != 6:
    print """
    Usage: %s <oldzip> <newsource> <deb> <mygpoclient> <feedparser>

    With:
       <oldzip>, e.g. gpodder-2.12-win32.zip
       <newsource>, e.g. gpodder-2.14.tar.gz
       <deb>, e.g. gpodder_2.14-1_all.deb
       <mygpoclient>, e.g. mygpoclient-1.5.tar.gz
       <feedparser>, e.g. feedparser-5.0.1.tar.gz
    """ % sys.argv[0]
    sys.exit(1)

progname, old_zip, source_tgz, deb, mygpoclient_tgz, feedparser_tgz = sys.argv

print '-'*80
print 'gPodder Win32 Release Builder'
print '-'*80


m = re.match(r'gpodder-(\d+).(\d+)-win32.zip', old_zip)
if not m:
    print 'Unknown filename scheme for', old_zip
    sys.exit(1)

old_version = '.'.join(m.groups())
print 'Old version:', old_version

m = re.match(r'gpodder-(\d+).(\d+).tar.gz', source_tgz)
if not m:
    print 'Unknown filename scheme for', source_tgz
    sys.exit(1)

new_version = '.'.join(m.groups())
print 'New version:', new_version

m = re.match(r'gpodder_(\d+).(\d+)-(.*)_all.deb$', deb)
if not m:
    print 'Unknown filename scheme for', deb
    sys.exit(1)

deb_version = '.'.join(m.groups()[:2]) + '-' + m.group(3)
print 'Debian version:', deb_version

m = re.match(r'mygpoclient-(\d+).(\d+).tar.gz', mygpoclient_tgz)
if not m:
    print 'Unknown filename scheme for', mygpoclient_tgz
    sys.exit(1)

mygpoclient_version = '.'.join(m.groups())
print 'mygpoclient version:', mygpoclient_version

m = re.match(r'feedparser-(\d+).(\d+).(\d+).tar.gz', feedparser_tgz)
if not m:
    print 'Unknown filename scheme for', feedparser_tgz
    sys.exit(1)

feedparser_version = '.'.join(m.groups())
print 'feedparser version:', feedparser_version

print '-'*80

print 'Press any key to continue, Ctrl+C to abort.',
raw_input()

if not deb_version.startswith(new_version):
    print 'New version and Debian version mismatch:'
    print new_version, '<->', deb_version
    sys.exit(1)

def sh(*args, **kwargs):
    print '->', ' '.join(args[0])
    try:
        ret = subprocess.call(*args, **kwargs)
    except Exception, e:
        print e
        ret = -1
    if ret != 0:
        print 'EXIT STATUS:', ret
        sys.exit(1)

old_dir, _ = os.path.splitext(old_zip)
new_dir = old_dir.replace(old_version, new_version)
target_file = new_dir + '.zip'

source_dir = source_tgz[:-len('.tar.gz')]
deb_dir, _ = os.path.splitext(deb)

mygpoclient_dir = mygpoclient_tgz[:-len('.tar.gz')]
feedparser_dir = feedparser_tgz[:-len('.tar.gz')]

print 'Cleaning up...'
sh(['rm', '-rf', old_dir, new_dir, source_dir, deb_dir,
    mygpoclient_dir, feedparser_dir])

print 'Extracting...'
sh(['unzip', '-q', old_zip])
sh(['tar', 'xzf', source_tgz])
sh(['dpkg', '-X', deb, deb_dir], stdout=subprocess.PIPE)
sh(['tar', 'xzf', mygpoclient_tgz])
sh(['tar', 'xzf', feedparser_tgz])

print 'Renaming win32 folder...'
sh(['mv', old_dir, new_dir])

copy_files_direct = [
    'ChangeLog',
    'COPYING',
    'README',
    'data/credits.txt',
    'data/gpodder.png',
    'data/images/*',
    'data/ui/*.ui',
    'data/ui/desktop/*.ui',
]

print 'Replacing data files...'
for pattern in copy_files_direct:
    from_files = glob.glob(os.path.join(source_dir, pattern))
    to_files = glob.glob(os.path.join(new_dir, pattern))
    to_folder = os.path.dirname(os.path.join(new_dir, pattern))

    if to_files:
        sh(['rm']+to_files)

    if not os.path.exists(to_folder):
        sh(['mkdir', to_folder])

    if from_files:
        sh(['cp']+from_files+[to_folder])


print 'Copying translations...'
sh(['cp', '-r', os.path.join(deb_dir, 'usr', 'share', 'locale'), os.path.join(new_dir, 'share')])

print 'Copying icons...'
sh(['cp', '-r', os.path.join(deb_dir, 'usr', 'share', 'icons'), os.path.join(new_dir, 'icons')])

print 'Replacing Python package gpodder...'
sh(['rm', '-rf', os.path.join(new_dir, 'lib', 'site-packages', 'gpodder')])
sh(['cp', '-r', os.path.join(source_dir, 'src', 'gpodder'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Replacing Python package mygpoclient...'
sh(['rm', '-rf', os.path.join(new_dir, 'lib', 'site-packages', 'mygpoclient')])
sh(['cp', '-r', os.path.join(mygpoclient_dir, 'mygpoclient'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Replacing Python module feedparser...'
sh(['rm', '-f', os.path.join(new_dir, 'lib', 'site-packages', 'feedparser.py')])
sh(['cp', os.path.join(feedparser_dir, 'feedparser', 'feedparser.py'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Building release...'
sh(['rm', '-f', target_file])
sh(['zip', '-qr', target_file, new_dir])

print 'Cleaning up...'
sh(['rm', '-rf', old_dir, new_dir, source_dir, deb_dir,
    mygpoclient_dir, feedparser_dir])

print '-'*80 + '\n'
print 'Successfully built gpodder', new_version, 'win32 release:'
print ' ', target_file, '\n'

