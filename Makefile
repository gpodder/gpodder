#
# gpodder makefile
# copyright 2005 thomas perl <thp@perli.net>
# released under the gnu gpl
#

##########################################################################

BINFILE=bin/gpodder
GLADEFILE=data/gpodder.glade
GUIFILE=src/gpodder/gpodder.py
MANPAGE=doc/man/gpodder.man.1

##########################################################################

all:

##########################################################################

test:
	$(BINFILE) --debug

deb:
	@echo "##########################################################################"
	@echo "# This is still alpha, see doc/dev/debian.txt for more info.             #"
	@echo "##########################################################################"
	python setup.py bdist_deb --maintainer "Peter Hoffmann <tosh@cs.tu-berlin.de>"  --extra-depends "python-gtk2, python-glade2, python-xml, wget"

release: generators
	python setup.py sdist

install: generators
	python setup.py install

uninstall:
	@echo "##########################################################################"
	@echo "#  MAKE UNINSTALL STILL NOT READY FOR PRIME TIME, WILL DO MY BEST TO     #"
	@echo "#  REMOVE FILES INSTALLED BY GPODDER. WATCH INSTALL PROCESS AND REMOVE   #"
	@echo "#  THE REST OF THE PACKAGES MANUALLY TO COMPLETELY REMOVE GPODDER.       #"
	@echo "##########################################################################"
	rm -rf /usr/share/gpodder /usr/share/applications/gpodder.desktop /usr/share/man/man1/gpodder.man.1 /usr/bin/gpodder /usr/lib/python?.?/site-packages/gpodder/

##########################################################################

generators: gen_manpage gen_glade

gen_manpage:
	help2man -N ./bin/gpodder >$(MANPAGE)

gen_glade: $(GLADEFILE)
	tepache --no-helper --glade=$(GLADEFILE) --output=$(GUIFILE)
	chmod -x $(GUIFILE) $(GUIFILE).orig

##########################################################################

clean:
	python setup.py clean
	rm -f src/gpodder/*.pyc src/gpodder/*.bak MANIFEST $(MANPAGE) PKG-INFO data/gpodder.gladep{,.bak} data/gpodder.glade.bak
	rm -rf build

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: all test release install generators gen_manpage gen_glade clean distclean

##########################################################################


