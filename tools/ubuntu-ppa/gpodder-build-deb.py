#!/bin/sh
# Build gPodder source package
# 2014-10-29 Thomas Perl <thp@gpodder.org>
# Based on generate-ubuntu-source.sh, 2009-09-23 Thomas Perl

import urllib2
import re
import subprocess
import os
import os.path
import shutil
import glob
import sys

def check_arg(arg):
    if arg in sys.argv:
        sys.argv.remove(arg)
        return True
    return False

os.environ['NAME'] = 'Thomas Perl'
os.environ['DEBEMAIL'] = 'thp@gpodder.org'

# Debian source package directory
debian_url = 'http://ftp.de.debian.org/debian/pool/main/g/gpodder/'

build_ubuntu_source = check_arg('--build-ppa')
build_debian_package = check_arg('--build-deb')

# See https://wiki.ubuntu.com/Releases
supported_ubuntu_releases = ['precise', 'trusty', 'utopic']

def read(url):
    return urllib2.urlopen(url).read()

def sh(*args):
    print args
    subprocess.check_call(args)

version_key = lambda s: [int(x) for x in s.split('.')]

deb_versions = re.findall(r'gpodder_([0-9.]+)-([0-9]+)\.dsc', read(debian_url))
deb_versions = sorted(deb_versions, key=lambda (v, r): (version_key(v), int(r)), reverse=True)
latest_deb_version, latest_deb_release = deb_versions[0]

dsc = '%(debian_url)sgpodder_%(latest_deb_version)s-%(latest_deb_release)s.dsc' % locals()

# Download source and update with latest upstream version
def get_source_tarball():
    if len(sys.argv) == 2:
        tar = sys.argv[1]
        latest_upstream_version = re.search('gpodder-([0-9.]+).tar.gz', tar).group(1)
        return latest_upstream_version, tar, False
    else:
        # upstream source package directory
        upstream_url = 'http://gpodder.org/src/'
        upstream_versions = re.findall(r'gpodder-([0-9.]+)\.tar\.gz', read(upstream_url))
        upstream_versions = sorted(upstream_versions, key=version_key, reverse=True)
        latest_upstream_version = upstream_versions[0]
        tar = '%(upstream_url)sgpodder-%(latest_upstream_version)s.tar.gz' % locals()
        sh('wget', '-N', tar)
        return latest_upstream_version, os.path.basename(tar), True

latest_upstream_version, tar, unlink_tar = get_source_tarball()
sh('dget', '--allow-unauthenticated', '--extract', dsc)
os.chdir('gpodder-%(latest_deb_version)s' % locals())
sh('uupdate', '--no-symlink', os.path.join('..', tar))
if unlink_tar:
    os.unlink(os.path.join('..', tar))
os.chdir(os.path.join('..', 'gpodder-%(latest_upstream_version)s' % locals()))
shutil.rmtree(os.path.join('..', 'gpodder-%(latest_deb_version)s' % locals()))
shutil.rmtree(os.path.join('..', 'gpodder-%(latest_upstream_version)s.orig' % locals()))
sh('rm', '-f', *glob.glob(os.path.join('..', 'gpodder_%(latest_deb_version)s*' % locals())))

dist = 'unstable'
folder = 'gpodder-%(latest_upstream_version)s' % locals()
version = '%(latest_upstream_version)s-1~gpo0' % locals()

sh('dch', '--distribution', dist, '--force-bad-version', '--preserve',
	'--newversion', version, 'Automatic build for %(dist)s' % locals())
sh('dpkg-buildpackage', '-sa', '-us', '-uc')
os.chdir('..')
shutil.rmtree(folder)
if build_debian_package:
    os.rename('gpodder_%(version)s_all.deb' % locals(),
            'gpodder_%(latest_upstream_version)s.deb' % locals())
files_to_delete_later = glob.glob('gpodder_%(version)s*' % locals())

dsc = 'gpodder_%(version)s.dsc' % locals()

if build_ubuntu_source:
    for dist in supported_ubuntu_releases:
        sh('dpkg-source', '-x', dsc)
        os.chdir(folder)
        new_version = '%(version)s~ppa~%(dist)s0' % locals()
        sh('dch', '--distribution', dist, '--force-bad-version', '--preserve',
            '--newversion', new_version, 'Automatic build for %(dist)s' % locals())
        sh('dpkg-buildpackage', '-S', '-sa', '-us', '-uc')
        os.chdir('..')
        shutil.rmtree(folder)
        print """

         To sign and upload the packages to the PPA:

               debsign *.changes
               dput ppa:thp/gpodder *.changes

        """
else:
    files_to_delete_later.append('gpodder_%(latest_upstream_version)s.orig.tar.gz' % locals())

sh('rm', '-f', *files_to_delete_later)

