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

all: generators

##########################################################################

test: generators
	$(BINFILE) --debug

release: generators
	python setup.py sdist

install: generators
	python setup.py install

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
	rm -f src/gpodder/*.pyc src/gpodder/*.bak MANIFEST $(MANPAGE) PKG-INFO
	rm -rf build

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: all test release install generators gen_manpage gen_glade clean distclean

##########################################################################


