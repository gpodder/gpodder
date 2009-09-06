#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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

##########################################################################

BINFILE=bin/gpodder
MESSAGESPOT=data/messages.pot
UIFILES=$(wildcard data/ui/*.ui)
UIFILES_H=$(subst .ui,.ui.h,$(UIFILES))
GUIFILE=src/gpodder/gui.py
HELP2MAN=help2man
MANPAGE=doc/man/gpodder.1
GPODDERVERSION=`cat $(BINFILE) |grep ^__version__.*=|cut -d\" -f2`

GPODDER_ICON_THEME=dist/gpodder

ROSETTA_FILES=$(MESSAGESPOT) data/po/*.po
ROSETTA_ARCHIVE=gpodder-rosetta-upload.tar.gz

CHANGELOG=ChangeLog
CHANGELOG_TMP=.ChangeLog.tmp
CHANGELOG_EDT=.ChangeLog.edit
CHANGELOG_BKP=.ChangeLog.backup
EMAIL ?= $$USER@`hostname -f`

DESTDIR ?= /
PREFIX ?= /usr

# default editor of user has not set "EDITOR" env variable
EDITOR ?= vim

##########################################################################

all: help

help:
	@echo 'make test            run gpodder in local directory'
	@echo 'make unittest        run doctests + unittests'
	@echo 'make mtest           run gpodder (for maemo scratchbox)'
	@echo 'make release         create source tarball in "dist/"'
	@echo 'make releasetest     run some tests before the release'
	@echo 'make install         install gpodder into "$(PREFIX)"'
	@echo 'make uninstall       uninstall gpodder from "$(PREFIX)"'
	@echo 'make generators      generate manpage and icons (if needed)'
	@echo 'make messages        rebuild messages.pot from new source'
	@echo 'make rosetta-upload  generate a tarball of all translation files'
	@echo 'make clean           remove generated+temp+*.py{c,o} files'
	@echo 'make distclean       do a "make clean" + remove "dist/"'
	@echo ''
	@echo 'make install-git-menuitem   Add shortcuts to your menu for this git checkout'
	@echo 'make remove-git-menuitem    Remove shortcuts created by "install-git-menuitem"'
	@echo ''
	@echo '(1) Please set environment variable "EMAIL" to your e-mail address'

##########################################################################

test:
	@# set xterm title to know what this window does ;)
	@echo -ne '\033]0;gPodder console (make test)\007'
	$(BINFILE) --verbose

unittest:
	PYTHONPATH=src/ python -m gpodder.unittests

mtest:
	@# in maemo scratchbox, we need this for osso/hildon
	run-standalone.sh python2.5 $(BINFILE) --maemo --verbose

deb:
	debuild

release: distclean
	python setup.py sdist

releasetest: unittest
	desktop-file-validate data/gpodder.desktop
	make -C data/po validate

install: generators
	python setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

update-icons:
	gtk-update-icon-cache -f -i $(PREFIX)/share/icons/hicolor/

uninstall:
	@echo "##########################################################################"
	@echo "#  MAKE UNINSTALL STILL NOT READY FOR PRIME TIME, WILL DO MY BEST TO     #"
	@echo "#  REMOVE FILES INSTALLED BY GPODDER. WATCH INSTALL PROCESS AND REMOVE   #"
	@echo "#  THE REST OF THE PACKAGES MANUALLY TO COMPLETELY REMOVE GPODDER.       #"
	@echo "##########################################################################"
	rm -rf $(PREFIX)/share/gpodder $(PREFIX)/share/pixmaps/gpodder* $(PREFIX)/share/applications/gpodder.desktop $(PREFIX)/share/man/man1/gpodder.1 $(PREFIX)/bin/gpodder $(PREFIX)/lib/python?.?/site-packages/gpodder/ $(PREFIX)/share/locale/*/LC_MESSAGES/gpodder.mo

##########################################################################

generators: $(MANPAGE)
	make -C data/po update

messages: gen_gettext

$(MANPAGE): src/gpodder/__init__.py
	$(HELP2MAN) --name="A Media aggregator and Podcast catcher" -N $(BINFILE) >$(MANPAGE)

gen_gettext: $(MESSAGESPOT)
	make -C data/po generators
	make -C data/po update

data/ui/%.ui.h: $(subst .ui.h,.h,$@)
	intltool-extract --type=gettext/glade $(subst .ui.h,.ui,$@)

$(MESSAGESPOT): src/gpodder/*.py $(GLADEGETTEXT) $(BINFILE) $(UIFILES_H)
	xgettext -k_ -kN_ -o $(MESSAGESPOT) src/gpodder/*.py $(UIFILES_H) $(BINFILE)
	sed -i'~' -e 's/SOME DESCRIPTIVE TITLE/gPodder translation template/g' -e 's/YEAR THE PACKAGE'"'"'S COPYRIGHT HOLDER/2006 Thomas Perl/g' -e 's/FIRST AUTHOR <EMAIL@ADDRESS>, YEAR/Thomas Perl <thp@perli.net>, 2006/g' -e 's/PACKAGE VERSION/gPodder '$(GPODDERVERSION)'/g' -e 's/PACKAGE/gPodder/g' $(MESSAGESPOT)

rosetta-upload: $(ROSETTA_ARCHIVE)
	@echo 'You can now upload the archive to launchpad.net:  ' $(ROSETTA_ARCHIVE)

$(ROSETTA_ARCHIVE):
	tar czvf $(ROSETTA_ARCHIVE) $(ROSETTA_FILES)

install-git-menuitem:
	doc/dev/install-desktopentry.sh

remove-git-menuitem:
	doc/dev/install-desktopentry.sh --remove

gpodder-icon-theme:
	rm -rf $(GPODDER_ICON_THEME)
	mkdir -p $(GPODDER_ICON_THEME)
	python doc/dev/icon-theme/list-icon-names.py >$(GPODDER_ICON_THEME)/names
	(cd $(GPODDER_ICON_THEME) && \
	    python ../../doc/dev/icon-theme/pack-icons.py && \
	    python ../../doc/dev/icon-theme/create-index.py >index.theme && \
	    gtk-update-icon-cache . && \
	    rm -f names)

##########################################################################

clean:
	python setup.py clean
	rm -f src/gpodder/*.pyc src/gpodder/gtkui/*.pyc src/gpodder/gtkui/interface/*.pyc src/gpodder/gtkui/maemo/*.pyc src/gpodder/gtkui/desktop/*.pyc src/gpodder/*.pyo src/gpodder/*.bak MANIFEST PKG-INFO $(UIFILES_H) data/messages.pot~ data/gpodder-??x??.png $(ROSETTA_ARCHIVE) .coverage
	rm -rf build
	make -C data/po clean

debclean:
	fakeroot debian/rules clean

distclean: clean
	rm -rf dist
 
##########################################################################

.PHONY: all test unittest release releasetest install update-icons generators gen_manpage gen_graphics clean distclean messages help install-git-menuitem remove-git-menuitem

##########################################################################


