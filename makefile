#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

BINFILE = bin/gpodder
MESSAGESPOT = po/messages.pot
POFILES = $(wildcard po/*.po)
MANPAGE = share/man/man1/gpodder.1

UIFILES=$(wildcard share/gpodder/ui/gtk/*.ui)
UIFILES_H=$(subst .ui,.ui.h,$(UIFILES))
QMLFILES=$(wildcard share/gpodder/ui/qml/*.qml)
TRANSLATABLE_SOURCE=$(wildcard src/gpodder/*.py \
		               src/gpodder/gtkui/*.py \
		               src/gpodder/gtkui/interface/*.py \
			       src/gpodder/gtkui/desktop/*.py \
			       src/gpodder/qmlui/*.py \
			       src/gpodder/webui/*.py \
			       src/gpodder/plugins/*.py \
			       share/gpodder/extensions/*.py)

GPODDER_SERVICE_FILE=share/dbus-1/services/org.gpodder.service
GPODDER_SERVICE_FILE_IN=$(addsuffix .in,$(GPODDER_SERVICE_FILE))

GPODDER_DESKTOP_FILE=share/applications/gpodder.desktop
GPODDER_DESKTOP_FILE_IN=$(addsuffix .in,$(GPODDER_DESKTOP_FILE))
GPODDER_DESKTOP_FILE_H=$(addsuffix .h,$(GPODDER_DESKTOP_FILE_IN))

DESTDIR ?= /
PREFIX ?= /usr

PYTHON ?= python
HELP2MAN ?= help2man

##########################################################################

help:
	@cat tools/make-help.txt

##########################################################################

unittest:
	PYTHONPATH=src/ $(PYTHON) -m gpodder.unittests

deb:
	debuild

release: distclean
	$(PYTHON) setup.py sdist

releasetest: unittest $(GPODDER_DESKTOP_FILE)
	desktop-file-validate $(GPODDER_DESKTOP_FILE)
	sh po/validate.sh

$(GPODDER_SERVICE_FILE): $(GPODDER_SERVICE_FILE_IN)
	sed -e 's#__PREFIX__#$(PREFIX)#' $< >$@

$(GPODDER_DESKTOP_FILE): $(GPODDER_DESKTOP_FILE_IN) $(POFILES)
	intltool-merge -d -u po $< $@

$(GPODDER_DESKTOP_FILE_IN).h: $(GPODDER_DESKTOP_FILE_IN)
	intltool-extract --quiet --type=gettext/ini $<

install: messages $(GPODDER_SERVICE_FILE) $(GPODDER_DESKTOP_FILE)
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

##########################################################################

manpage: $(MANPAGE)

$(MANPAGE): src/gpodder/__init__.py $(BINFILE)
	$(HELP2MAN) --name="$(shell $(PYTHON) setup.py --description)" -N $(BINFILE) >$(MANPAGE)

##########################################################################

messages: $(MESSAGESPOT)
	$(MAKE) -C po

%.ui.h: $(UIFILES)
	intltool-extract --quiet --type=gettext/glade $(subst .ui.h,.ui,$@)

$(MESSAGESPOT): $(TRANSLATABLE_SOURCE) $(UIFILES_H) $(QMLFILES) $(BINFILE) $(GPODDER_DESKTOP_FILE_H)
	xgettext -LPython -k_:1 -kN_:1 -kN_:1,2 -kn_:1,2 -o $(MESSAGESPOT) $^

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
	find src/ '(' -name '*.pyc' -o -name '*.pyo' ')' -exec rm '{}' +
	find src/ -type d -name '__pycache__' -exec rm -r '{}' +
	find share/gpodder/ui/ -name '*.ui.h' -exec rm '{}' +
	rm -f MANIFEST PKG-INFO .coverage messages.mo
	rm -f $(GPODDER_SERVICE_FILE)
	rm -f $(GPODDER_DESKTOP_FILE)
	rm -f $(GPODDER_DESKTOP_FILE_H)
	rm -rf build
	$(MAKE) -C po clean

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: help unittest release releasetest install manpage clean distclean messages headlink

##########################################################################


