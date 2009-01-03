#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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
update:
	for langfile in *.po; do echo 'Compiling translation:' $${langfile}; mkdir -p ../locale/`basename $${langfile} .po`/LC_MESSAGES/; msgfmt $${langfile} -o ../locale/`basename $${langfile} .po`/LC_MESSAGES/gpodder.mo; done

generators:
	for langfile in *.po; do echo -n $${langfile}; msgmerge -U $${langfile} ../messages.pot; done

clean:
	rm -rf ../locale *~ *.mo

statistics:
	@for file in *.po; do echo -n "$$file (`cat $$file | grep Revision-Date | cut -d' ' -f2`): "; msgfmt --statistics $$file 2>&1; done


.PHONY: update generators clean statistics

