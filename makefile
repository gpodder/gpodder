#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
	           data/ui/desktop/*.ui)
UIFILES_H=$(subst .ui,.ui.h,$(UIFILES))
TRANSLATABLE_SOURCE=$(wildcard src/gpodder/*.py \
		               src/gpodder/gtkui/*.py \
		               src/gpodder/gtkui/interface/*.py \
			       src/gpodder/gtkui/desktop/*.py)

HELP2MAN=help2man
MANPAGE=data/man/gpodder.1

GPODDER_SERVICE_FILE=data/org.gpodder.service
GPODDER_SERVICE_FILE_IN=$(addsuffix .in,$(GPODDER_SERVICE_FILE))

GPODDER_DESKTOP_FILE=data/gpodder.desktop
GPODDER_DESKTOP_FILE_IN=$(addsuffix .in,$(GPODDER_DESKTOP_FILE))
DESKTOPFILE_H=$(addsuffix .h,$(GPODDER_DESKTOP_FILE_IN))

DESTDIR ?= /
PREFIX ?= /usr

PYTHON ?= python

##########################################################################

all: help

help:
	@echo 'make test            run gpodder in local directory'
	@echo 'make qmltest         run gpodder (qml ui) in local directory'
	@echo 'make unittest        run doctests + unittests'
	@echo 'make release         create source tarball in "dist/"'
	@echo 'make releasetest     run some tests before the release'
	@echo 'make install         install gpodder into "$(PREFIX)"'
	@echo 'make manpage         update manpage (on release)'
	@echo 'make messages        update messages.pot + .po files + .mo files'
	@echo 'make clean           remove generated+temp+*.py{c,o} files'
	@echo 'make distclean       do a "make clean" + remove "dist/"'
	@echo 'make headlink        print URL for the current Git head'

##########################################################################

test:
	@# set xterm title to know what this window does ;)
	@echo -ne '\033]0;gPodder console (make test)\007'
	$(BINFILE) --verbose

qmltest:
	@echo -ne '\033]0;gPodder/QML console\007'
	$(BINFILE) --qml --verbose

unittest:
	PYTHONPATH=src/ $(PYTHON) -m gpodder.unittests

deb:
	debuild

release: distclean
	$(PYTHON) setup.py sdist

releasetest: unittest $(GPODDER_DESKTOP_FILE)
	desktop-file-validate $(GPODDER_DESKTOP_FILE)
	make -C data/po validate

$(GPODDER_SERVICE_FILE): $(GPODDER_SERVICE_FILE_IN)
	sed -e 's#__PREFIX__#$(PREFIX)#' $< >$@

$(GPODDER_DESKTOP_FILE): $(GPODDER_DESKTOP_FILE_IN) data/po/*.po
	intltool-merge -d -u data/po $< $@

$(GPODDER_DESKTOP_FILE_IN).h: $(GPODDER_DESKTOP_FILE_IN)
	intltool-extract --quiet --type=gettext/ini $<

install: messages $(GPODDER_SERVICE_FILE) $(GPODDER_DESKTOP_FILE)
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

##########################################################################

manpage: $(MANPAGE)

$(MANPAGE): src/gpodder/__init__.py $(BINFILE)
	$(HELP2MAN) --name="A Media aggregator and Podcast catcher" -N $(BINFILE) >$(MANPAGE)

##########################################################################

messages: $(MESSAGESPOT)
	make -C data/po

data/ui/%.ui.h: $(UIFILES)
	intltool-extract --quiet --type=gettext/glade $(subst .ui.h,.ui,$@)

$(MESSAGESPOT): $(TRANSLATABLE_SOURCE) $(UIFILES_H) $(BINFILE) $(DESKTOPFILE_H)
	xgettext -k_:1 -kN_:1 -kN_:1,2 -o $(MESSAGESPOT) $^

##########################################################################

# This only works in a Git working commit, and assumes that the local Git
# HEAD has already been pushed to the main repository. It's mainly useful
# for the gPodder maintainer to quickly generate a commit link that can be
# posted online in bug trackers and mailing lists.

headlink:
	@echo http://gpodder.org/commit/`git show-ref HEAD | head -c8`

##########################################################################

clean:
	$(PYTHON) setup.py clean
	find src/ -name '*.pyc' -exec rm '{}' \;
	find src/ -name '*.pyo' -exec rm '{}' \;
	find data/ui/ -name '*.ui.h' -exec rm '{}' \;
	rm -f MANIFEST PKG-INFO data/messages.pot~ $(DESKTOPFILE_H)
	rm -f data/gpodder-??x??.png .coverage
	rm -f $(GPODDER_SERVICE_FILE) $(GPODDER_DESKTOP_FILE)
	rm -rf build
	make -C data/po clean

debclean:
	fakeroot debian/rules clean

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: all test unittest release releasetest install manpage clean distclean messages help headlink

##########################################################################


