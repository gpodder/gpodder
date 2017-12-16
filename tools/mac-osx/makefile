#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2017 Thomas Perl and the gPodder Team
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
#
# the installed path of the gpodder script
GPODDERSCRIPT=/Users/elelay/misc/macports/svnlocal_dports/gnome/gpodder/gpodder/bin/gpodder
# the /Applications directory
APPLICATIONSDIR=/tmp/Applications
APPDIR=$(APPLICATIONSDIR)/gPodder.app
BINDIR=$(APPDIR)/Contents/MacOS
RESOURCESDIR=$(APPDIR)/Contents/Resources
# current version of gPodder
VERSION=2.3

# set OSXVERSION to darwin8 to get the Mac OS X Tiger version of the plist.
OSXVERSION=darwin8
ifeq ($(OSXVERSION),darwin8)
PLIST=Info-10.4.plist
else
PLIST=Info.plist
endif

all:$(BINDIR)/gpodder\
	$(RESOURCESDIR)/icon.icns\
	$(APPDIR)/Contents/PkgInfo\
	$(APPDIR)/Contents/Info.plist

$(BINDIR):
	mkdir -p $(BINDIR)

$(RESOURCESDIR):
	mkdir -p $(RESOURCESDIR)

$(BINDIR)/gpodder: ../../bin/gpodder $(BINDIR)
	ln -s $(GPODDERSCRIPT) $@

$(RESOURCESDIR)/icon.icns: icon.icns $(RESOURCESDIR)
	install $< $@

$(APPDIR)/Contents/PkgInfo: PkgInfo $(RESOURCESDIR)
	install $< $@

$(APPDIR)/Contents/Info.plist: $(PLIST) $(APPDIR)/Contents
	sed "s|__VERSION__|$(VERSION)|g" $< > $@

clean:
	rm -rf $(APPDIR)

.PHONY: all clean dirs
