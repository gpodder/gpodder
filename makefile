#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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
MANPAGES = share/man/man1/gpodder.1 share/man/man1/gpo.1

GPODDER_SERVICE_FILE=share/dbus-1/services/org.gpodder.service
GPODDER_SERVICE_FILE_IN=$(addsuffix .in,$(GPODDER_SERVICE_FILE))

DESKTOP_FILES_IN=$(wildcard share/applications/*.desktop.in)
DESKTOP_FILES_IN_H=$(patsubst %.desktop.in,%.desktop.in.h,$(DESKTOP_FILES_IN))
DESKTOP_FILES=$(patsubst %.desktop.in,%.desktop,$(DESKTOP_FILES_IN))

MESSAGES = po/messages.pot
POFILES = $(wildcard po/*.po)
LOCALEDIR = share/locale
MOFILES = $(patsubst po/%.po,$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo, $(POFILES))

UIFILES=$(wildcard share/gpodder/ui/gtk/*.ui)
UIFILES_H=$(subst .ui,.ui.h,$(UIFILES))
GETTEXT_SOURCE=$(wildcard src/gpodder/*.py \
			  src/gpodder/gtkui/*.py \
			  src/gpodder/gtkui/interface/*.py \
			  src/gpodder/gtkui/desktop/*.py \
			  src/gpodder/plugins/*.py \
			  share/gpodder/extensions/*.py)

GETTEXT_SOURCE += $(UIFILES_H)
GETTEXT_SOURCE += $(wildcard bin/*[^~])
GETTEXT_SOURCE += $(DESKTOP_FILES_IN_H)

DESTDIR ?= /
PREFIX ?= /usr

PYTHON ?= python3
HELP2MAN ?= help2man

PYTEST ?= $(shell which pytest || which pytest-3)

##########################################################################

help:
	@cat tools/make-help.txt

##########################################################################

unittest:
	LC_ALL=C PYTHONPATH=src/ $(PYTEST) --ignore=tests --ignore=src/gpodder/utilwin32ctypes.py --doctest-modules src/gpodder/util.py src/gpodder/jsonconfig.py
	LC_ALL=C PYTHONPATH=src/ $(PYTEST) tests --ignore=src/gpodder/utilwin32ctypes.py --ignore=src/mygpoclient --cov=gpodder

ISORTOPTS := -c share src/gpodder tools bin/* *.py
lint:
	pycodestyle --version
	pycodestyle share src/gpodder tools bin/* *.py

	isort --version
	isort -q $(ISORTOPTS) || isort --df $(ISORTOPTS)
	codespell --quiet-level 3 --skip "./.git,*.po,./share/applications/gpodder.desktop"

release: distclean
	$(PYTHON) setup.py sdist

releasetest: unittest $(DESKTOP_FILES) $(POFILES)
	for f in $(DESKTOP_FILES); do desktop-file-validate $$f || exit 1; done
	for f in $(POFILES); do msgfmt --check $$f || exit 1; done

$(GPODDER_SERVICE_FILE): $(GPODDER_SERVICE_FILE_IN)
	sed -e 's#__PREFIX__#$(PREFIX)#' $< >$@

%.desktop: %.desktop.in $(POFILES)
	sed -e 's#__PREFIX__#$(PREFIX)#' $< >$@.tmp
	intltool-merge -d -u po $@.tmp $@
	rm -f $@.tmp

%.desktop.in.h: %.desktop.in
	intltool-extract --quiet --type=gettext/ini $<

install: messages $(GPODDER_SERVICE_FILE) $(DESKTOP_FILES)
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX) --optimize=1

install-win: messages $(GPODDER_SERVICE_FILE) $(DESKTOP_FILES)
	$(PYTHON) setup.py install

##########################################################################
ifdef VERSION
revbump:
	LC_ALL=C sed -i "s/\(__version__\s*=\s*'\).*'/\1$(VERSION)'/" src/gpodder/__init__.py
	LC_ALL=C sed -i "s/\(__date__\s*=\s*'\).*'/\1$(shell date "+%Y-%m-%d")'/" src/gpodder/__init__.py
	LC_ALL=C sed -i "s/\(__copyright__\s*=.*2005-\)[0-9]*\(.*\)/\1$(shell date "+%Y")\2/" src/gpodder/__init__.py
	$(MAKE) messages manpages
else
revbump:
	@echo "Usage: make revbump VERSION=x.y.z"
endif
##########################################################################

manpages: $(MANPAGES)

share/man/man1/gpodder.1: src/gpodder/__init__.py $(BINFILE)
	LC_ALL=C $(HELP2MAN) --name="$(shell $(PYTHON) setup.py --description)" -N $(BINFILE) >$@

share/man/man1/gpo.1: src/gpodder/__init__.py
	sed -i 's/^\.TH.*/.TH GPO "1" "$(shell LANG=en date "+%B %Y")" "gpodder $(shell $(PYTHON) setup.py --version)" "User Commands"/' $@

##########################################################################

messages: $(MOFILES)

%.po: $(MESSAGES)
	msgmerge --previous --silent $@ $< --output-file=$@
	msgattrib --set-obsolete --ignore-file=$< -o $@ $@
	msgattrib --no-obsolete -o $@ $@

$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo: po/%.po
	@mkdir -p $(@D)
	msgfmt $< -o $@

%.ui.h: %.ui
	intltool-extract --quiet --type=gettext/glade $<

$(MESSAGES): $(GETTEXT_SOURCE)
	xgettext --from-code=utf-8 -LPython -k_:1 -kN_:1 -kN_:1,2 -kn_:1,2 -o $(MESSAGES) $^

messages-force:
	xgettext --from-code=utf-8 -LPython -k_:1 -kN_:1 -kN_:1,2 -kn_:1,2 -o $(MESSAGES)  $(GETTEXT_SOURCE)

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
	rm -f MANIFEST .coverage messages.mo po/*.mo
	rm -f $(GPODDER_SERVICE_FILE)
	rm -f $(DESKTOP_FILES) $(DESKTOP_FILES_IN_H)
	rm -rf build $(LOCALEDIR)

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: help unittest release releasetest install manpages clean distclean messages headlink lint revbump

##########################################################################
