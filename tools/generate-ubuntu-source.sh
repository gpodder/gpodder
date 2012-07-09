#!/bin/sh
# Generate Ubuntu derivations of a normal Debian package source
# 2009-09-23 Thomas Perl

SOURCEFILE=$1
VERSION=`echo $SOURCEFILE | sed -e 's/[^_]*_\(.*\)-[^-]*\.dsc/\1/g'`
FOLDER=`echo $SOURCEFILE | sed -e 's/\([^_]*\)_.*/\1/g'`-${VERSION}

# See https://wiki.ubuntu.com/DevelopmentCodeNames
UBUNTU_RELEASES="maverick natty oneiric precise quantal"

echo "SOURCEFILE = $SOURCEFILE"
echo "VERSION    = $VERSION"
echo "FOLDER     = $FOLDER"

for DIST in $UBUNTU_RELEASES; do
    dpkg-source -x $SOURCEFILE
    cd $FOLDER

    VERSION=`dpkg-parsechangelog | awk '/^Version: / {print $2}'`
    NEW_VERSION=${VERSION}~${DIST}0

    dch --distribution ${DIST} \
        --force-bad-version --preserve \
        --newversion ${NEW_VERSION} "Automatic build for ${DIST}"

    dpkg-buildpackage -S -sa -us -uc
    cd ..
    rm -rf $FOLDER
done

debsign *.changes

echo
echo " If signing (as oppposed to singing) went well, do this now:"
echo
echo "       dput ppa:thp/gpodder *.changes"
echo

