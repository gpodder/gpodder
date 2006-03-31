#
# gpodder makefile
# copyright 2005-2006 thomas perl <thp@perli.net>
# released under the gnu gpl
#

##########################################################################

BINFILE=bin/gpodder
GLADEFILE=data/gpodder.glade
GLADEGETTEXT=$(GLADEFILE).h
MESSAGESPOT=data/messages.pot
GUIFILE=src/gpodder/gpodder.py
MANPAGE=doc/man/gpodder.man.1
TEPACHE=./doc/dev/tepache
GPODDERVERSION=`cat $(BINFILE) |grep ^__version__.*=|cut -d\" -f2`

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
	rm -rf /usr/share/gpodder /usr/share/applications/gpodder.desktop /usr/share/man/man1/gpodder.man.1 /usr/bin/gpodder /usr/lib/python?.?/site-packages/gpodder/ /usr/share/locale/*/LC_MESSAGES/gpodder.mo

##########################################################################

generators: $(MANPAGE) gen_glade gen_gettext

$(MANPAGE): $(BINFILE)
	help2man -N $(BINFILE) >$(MANPAGE)

gen_glade: $(GLADEFILE)
	$(TEPACHE) --no-helper --glade=$(GLADEFILE) --output=$(GUIFILE)
	chmod -x $(GUIFILE) $(GUIFILE).orig

gen_gettext: $(MESSAGESPOT)
	make -C data/po

$(GLADEGETTEXT): $(GLADEFILE)
	intltool-extract --type=gettext/glade $(GLADEFILE)

$(MESSAGESPOT): src/gpodder/*.py $(GLADEGETTEXT) $(BINFILE)
	xgettext -j -k_ -kN_ -o $(MESSAGESPOT) src/gpodder/*.py $(GLADEGETTEXT) $(BINFILE)
	sed -e 's/SOME DESCRIPTIVE TITLE/gPodder translation template/g' -e 's/YEAR THE PACKAGE'"'"'S COPYRIGHT HOLDER/2006 Thomas Perl/g' -e 's/FIRST AUTHOR <EMAIL@ADDRESS>, YEAR/Thomas Perl <thp@perli.net>, 2006/g' -e 's/PACKAGE VERSION/gPodder '$(GPODDERVERSION)'/g' -e 's/PACKAGE/gPodder/g' $(MESSAGESPOT) > $(MESSAGESPOT).tmp
	mv $(MESSAGESPOT).tmp $(MESSAGESPOT)

##########################################################################

clean:
	python setup.py clean
	rm -f src/gpodder/*.pyc src/gpodder/*.bak MANIFEST PKG-INFO data/gpodder.gladep{,.bak} data/gpodder.glade.bak $(GLADEGETTEXT)
	rm -rf build
	make -C data/po clean

distclean: clean
	rm -rf dist

##########################################################################

.PHONY: all test release install generators gen_manpage gen_glade clean distclean

##########################################################################


