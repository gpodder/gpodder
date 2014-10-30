# gPodder Win32 Setup Cross-Build script
# 2014-10-21 Thomas Perl <m@thp.io>

PYTHON ?= python

VERSION := $(shell $(PYTHON) ../getversion.py)

SED := sed
CHMOD := chmod

# Simple script that calls ISCC.exe via Wine, and passes arguments
ISCC ?= iscc

SETUP_SCRIPT := gpodder-setup.iss
SETUP_SCRIPT_IN := $(SETUP_SCRIPT).in
SETUP_OUTPUT := gpodder-$(VERSION)-setup.exe

SOURCE_ROOT := ../../

LAUNCHER_ROOT := ../win32-launcher
GPODDER_EXE := gpodder.exe
GPO_EXE := gpo.exe

all: $(SETUP_OUTPUT)

$(SETUP_OUTPUT): $(SETUP_SCRIPT) $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
	$(PYTHON) ../localdepends.py
	cp -rpv ../fake-dbus-module/dbus ../../src/
	$(MAKE) -C $(SOURCE_ROOT) messages
	$(ISCC) $<
	$(CHMOD) -x $@

$(LAUNCHER_ROOT)/$(GPODDER_EXE):
	$(MAKE) -C $(LAUNCHER_ROOT) $(GPODDER_EXE)

$(LAUNCHER_ROOT)/$(GPO_EXE):
	$(MAKE) -C $(LAUNCHER_ROOT) $(GPO_EXE)

$(SETUP_SCRIPT): $(SETUP_SCRIPT_IN)
	$(RM) $@
	$(SED) -e "s#%VERSION%#$(VERSION)#g" $< >$@

clean:
	$(RM) $(SETUP_SCRIPT)
	$(MAKE) -C $(LAUNCHER_ROOT) distclean

distclean: clean
	$(RM) $(SETUP_OUTPUT)

.PHONY: all clean distclean $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
.DEFAULT: all
