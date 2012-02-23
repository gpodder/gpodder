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

PO_FILES = $(wildcard *.po)
POT_FILE = messages.pot

LOCALE_DIR = ../share/locale/

# Check for $LINGUAS presence.
ifeq ($(origin LINGUAS), undefined)
	PO_INSTALL = $(PO_FILES)
else
	PO_INSTALL = $(addsuffix .po,$(filter $(subst .po,,$(PO_FILES)),$(LINGUAS)))
endif

MO_FILES = $(addsuffix /LC_MESSAGES/gpodder.mo,$(addprefix $(LOCALE_DIR),$(subst .po,,$(PO_INSTALL))))

all: $(PO_INSTALL) $(MO_FILES)

%.po: $(POT_FILE)
	@echo "Merging $(notdir $<) -> $@"
	@msgmerge --silent $@ $< --output-file=$@

%.mo: $(PO_INSTALL)
	@echo "Compiling $(subst /LC_MESSAGES/gpodder.mo,.po,$(subst $(LOCALE_DIR),,$@)) -> $(notdir $@)"
	@mkdir -p $(@D)
	@msgfmt $(subst /LC_MESSAGES/gpodder.mo,.po,$(subst $(LOCALE_DIR),,$@)) -o $@

clean:
	rm -rf $(LOCALE_DIR) *.mo

.PHONY: all clean

