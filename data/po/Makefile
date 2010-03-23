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

PO_FILES=$(wildcard *.po)
POT_FILE=../messages.pot

# Check for $LINGUAS presence.
ifeq ($(origin LINGUAS), undefined)
	PO_INSTALL=$(PO_FILES)
else
	PO_INSTALL=$(addsuffix .po,$(filter $(subst .po,,$(PO_FILES)),$(LINGUAS)))
endif

MO_FILES=$(addsuffix /LC_MESSAGES/gpodder.mo,$(addprefix ../locale/,$(subst .po,,$(PO_INSTALL))))

all: $(PO_INSTALL) $(MO_FILES)

%.po: $(POT_FILE)
	@echo "Merging $(notdir $<) -> $@"
	@msgmerge --silent $@ $< --output-file=$@

%.mo: $(PO_INSTALL)
	@echo "Compiling $(subst /LC_MESSAGES/gpodder.mo,.po,$(subst ../locale/,,$@)) -> $(notdir $@)"
	@mkdir -p $(@D)
	@msgfmt $(subst /LC_MESSAGES/gpodder.mo,.po,$(subst ../locale/,,$@)) -o $@

clean:
	rm -rf ../locale *~ *.mo

statistics:
	@for file in *.po; do echo -n "$$file (`cat $$file | grep Revision-Date | cut -d' ' -f2`): "; msgfmt --statistics $$file 2>&1; done

validate:
	./validate.sh

.PHONY: all clean statistics validate

