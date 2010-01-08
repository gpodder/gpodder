#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

UIFILES=$(wildcard data/ui/*.ui \
	           data/ui/desktop/*.ui \
		   data/ui/maemo/*.ui \
		   data/ui/frmntl/*.ui)
UIFILES_H=$(subst .ui,.ui.h,$(UIFILES))
TRANSLATABLE_SOURCE=$(wildcard src/gpodder/*.py \
		               src/gpodder/gtkui/*.py \
		               src/gpodder/gtkui/interface/*.py \
			       src/gpodder/gtkui/desktop/*.py \
			       src/gpodder/gtkui/maemo/*.py \
			       src/gpodder/gtkui/frmntl/*.py)

HELP2MAN=help2man
MANPAGE=doc/man/gpodder.1

GPODDER_ICON_THEME=dist/gpodder

GPODDER_SERVICE_FILE=data/org.gpodder.service
GPODDER_SERVICE_FILE_IN=$(addsuffix .in,$(GPODDER_SERVICE_FILE))

DESTDIR ?= /
PREFIX ?= /usr

##########################################################################

all: help

help:
	@echo 'make test            run gpodder in local directory'
	@echo 'make unittest        run doctests + unittests'
	@echo 'make mtest           run gpodder (for maemo scratchbox)'
	@echo 'make release         create source tarball in "dist/"'
	@echo 'make releasetest     run some tests before the release'
	@echo 'make install         install gpodder into "$(PREFIX)"'
	@echo 'make manpage         update manpage (on release)'
	@echo 'make messages        update messages.pot + .po files + .mo files'
	@echo 'make clean           remove generated+temp+*.py{c,o} files'
	@echo 'make distclean       do a "make clean" + remove "dist/"'
	@echo ''
	@echo 'make install-git-menuitem   Add shortcuts to your menu for this git checkout'
	@echo 'make remove-git-menuitem    Remove shortcuts created by "install-git-menuitem"'

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

$(GPODDER_SERVICE_FILE): $(GPODDER_SERVICE_FILE_IN)
	sed -e 's#__PREFIX__#$(PREFIX)#' $< >$@

install: messages $(GPODDER_SERVICE_FILE)
	python setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

##########################################################################

manpage: $(MANPAGE)

$(MANPAGE): src/gpodder/__init__.py $(BINFILE)
	$(HELP2MAN) --name="A Media aggregator and Podcast catcher" -N $(BINFILE) >$(MANPAGE)

##########################################################################

messages: $(MESSAGESPOT)
	make -C data/po

data/ui/%.ui.h: $(UIFILES)
	intltool-extract --quiet --type=gettext/glade $(subst .ui.h,.ui,$@)

$(MESSAGESPOT): $(TRANSLATABLE_SOURCE) $(UIFILES_H) $(BINFILE)
	xgettext -k_:1 -kN_:1,2 -o $(MESSAGESPOT) $(TRANSLATABLE_SOURCE) $(UIFILES_H) $(BINFILE)

##########################################################################

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
	    rm -f names)

##########################################################################

clean:
	python setup.py clean
	find src/ -name '*.pyc' -exec rm '{}' \;
	find src/ -name '*.pyo' -exec rm '{}' \;
	rm -f MANIFEST PKG-INFO $(UIFILES_H) data/messages.pot~ data/gpodder-??x??.png .coverage $(GPODDER_SERVICE_FILE)
	rm -rf build
	make -C data/po clean

debclean:
	fakeroot debian/rules clean

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: all test unittest release releasetest install manpage clean distclean messages help install-git-menuitem remove-git-menuitem

##########################################################################


