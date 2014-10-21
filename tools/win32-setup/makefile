# gPodder Win32 Setup Cross-Build script
# 2014-10-21 Thomas Perl <m@thp.io>

PYTHON ?= python

VERSION := $(shell $(PYTHON) ../getversion.py)

CROSS_MAKE := mingw32-make
SED := sed
CHMOD := chmod

# We run the InnoSetup compiler via Wine (just install normally)
WINE := wine
ISCC := "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"

SETUP_SCRIPT := gpodder-setup.iss
SETUP_SCRIPT_IN := $(SETUP_SCRIPT).in
SETUP_OUTPUT := gpodder-$(VERSION)-setup.exe

LAUNCHER_ROOT := ../win32-launcher
GPODDER_EXE := gpodder.exe
GPO_EXE := gpo.exe

all: $(SETUP_OUTPUT)

$(SETUP_OUTPUT): $(SETUP_SCRIPT) $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
	$(WINE) $(ISCC) $<
	$(CHMOD) -x $@

$(LAUNCHER_ROOT)/$(GPODDER_EXE):
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) $(GPODDER_EXE)

$(LAUNCHER_ROOT)/$(GPO_EXE):
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) $(GPO_EXE)

$(SETUP_SCRIPT): $(SETUP_SCRIPT_IN)
	$(RM) $@
	$(SED) -e "s#%VERSION%#$(VERSION)#g" $< >$@

clean:
	$(RM) $(SETUP_SCRIPT)
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) distclean

distclean: clean
	$(RM) $(SETUP_OUTPUT)

.PHONY: all clean distclean $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
.DEFAULT: all
