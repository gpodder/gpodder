#
# gPodder: Media and podcast aggregator
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

##########################################################################

PYTHON ?= python3

##########################################################################

help:
	@echo ""
	@echo "  make messages       Update translation files in po/ from source"
	@echo "  make headlink       Print commit URL for the current Git head"
	@echo ""
	@echo "  make tests          Run tests"
	@echo "  make clean          Remove generated and compiled files"
	@echo "  make distclean      'make clean' + remove dist/"
	@echo ""
	@echo "  make release        Create the source tarball in dist/"
	@echo ""
	@echo "  make install        Install gPodder into \$$DESTDIR/\$$PREFIX"
	@echo ""
	@echo "         PREFIX ..... Installation prefix (default: /usr)"
	@echo "         DESTDIR .... Installation destination (default: /)"
	@echo "         LINGUAS .... Space-separated list of translations"
	@echo ""

##########################################################################

unittest:
	LC_ALL=C PYTHONPATH=src/ $(PYTHON) -m gpodder.test.__init__

parsertest:
	$(PYTHON) tools/test-parser/test_parser.py

releasetest: tests $(POFILES)
	for lang in $(POFILES); do $(MSGFMT) --check $$lang; done

tests: unittest parsertest

##########################################################################

release: releasetest distclean
	$(PYTHON) setup.py sdist

DESTDIR ?= /
PREFIX ?= /usr

install: messages
	$(PYTHON) setup.py install --root=$(DESTDIR) --prefix=$(PREFIX) --optimize=1

# This only works in a Git working commit, and assumes that the local Git
# HEAD has already been pushed to the main repository. It's mainly useful
# for the gPodder maintainer to quickly generate a commit link that can be
# posted online in bug trackers and mailing lists.

headlink:
	@echo http://gpodder.org/commit/$(shell git show-ref HEAD | head -c8)

##########################################################################

XGETTEXT ?= xgettext
MSGMERGE ?= msgmerge
MSGFMT ?= msgfmt

MESSAGES = po/messages.pot
POFILES = $(wildcard po/*.po)
LOCALEDIR = share/locale
MOFILES = $(patsubst po/%.po,$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo,$(POFILES))

messages: $(MESSAGES) $(MOFILES)

%.po: $(MESSAGES)
	$(MSGMERGE) --silent $@ $< --output-file=$@

$(LOCALEDIR)/%/LC_MESSAGES/gpodder.mo: po/%.po
	@mkdir -p $(@D)
	$(MSGFMT) $< -o $@

$(MESSAGES): bin/gpo
	$(XGETTEXT) --from-code=utf-8 --language=Python -k_:1 -kN_:1 -kN_:1,2 -o $(MESSAGES) $^

##########################################################################

clean:
	$(PYTHON) setup.py clean
	find src/ -type d -name '__pycache__' -exec rm -r '{}' +
	rm -f MANIFEST PKG-INFO .coverage messages.mo po/*.mo
	rm -rf build $(LOCALEDIR)

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: help \
    unittest parsertest releasetest tests \
    release install headlink messages \
    clean distclean \
