#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

MESSAGES = po/messages.pot
POFILES = $(wildcard po/*.po)
LOCALEDIR = share/locale
MOFILES = $(patsubst po/%.po,$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo, $(POFILES))

GETTEXT_SOURCE=$(wildcard bin/* \
	                  src/gpodder/*.py \
		          src/gpodder/compat/*.py \
			  src/gpodder/plugins/*.py)

DESTDIR ?= /
PREFIX ?= /usr

PYTHON ?= python3
XGETTEXT ?= xgettext

##########################################################################

help:
	@cat tools/make-help.txt

##########################################################################

unittest:
	LC_ALL=C PYTHONPATH=src/ $(PYTHON) -m gpodder.test.__init__

parsertest:
	$(PYTHON) tools/test-parser/test_parser.py

release: distclean
	$(PYTHON) setup.py sdist

releasetest: unittest $(POFILES)
	sh tools/i18n/validate.sh

install: messages
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX) --optimize=1

##########################################################################

messages: $(MOFILES)

%.po: $(MESSAGES)
	msgmerge --silent $@ $< --output-file=$@

$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo: po/%.po
	@mkdir -p $(@D)
	msgfmt $< -o $@

%.ui.h: %.ui
	intltool-extract --quiet --type=gettext/glade $<

$(MESSAGES): $(GETTEXT_SOURCE)
	$(XGETTEXT) -LPython -k_:1 -kN_:1 -kN_:1,2 -kn_:1,2 -o $(MESSAGES) $^

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
	rm -f MANIFEST PKG-INFO .coverage messages.mo po/*.mo
	rm -rf build $(LOCALEDIR)

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: help unittest parsertest release releasetest install clean distclean messages headlink

##########################################################################


