# gPodder Win32 Portable Cross-Build script
# 2014-10-21 Thomas Perl <m@thp.io>

PYTHON ?= python

VERSION := $(shell $(PYTHON) ../getversion.py)

CROSS_MAKE := mingw32-make
MKDIR := mkdir
CP := cp

PORTABLE_OUTPUT_DIR := gpodder-$(VERSION)-win32
PORTABLE_OUTPUT := $(PORTABLE_OUTPUT_DIR).zip

SOURCE_ROOT := ../../

LAUNCHER_ROOT := ../win32-launcher
GPODDER_EXE := gpodder.exe
GPO_EXE := gpo.exe

all: $(PORTABLE_OUTPUT)

$(PORTABLE_OUTPUT_DIR): $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
	$(PYTHON) ../localdepends.py
	$(MAKE) -C $(SOURCE_ROOT) messages
	$(RM) -r $(PORTABLE_OUTPUT_DIR)
	$(MKDIR) -p $(PORTABLE_OUTPUT_DIR)
	$(CP) $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE) $(PORTABLE_OUTPUT_DIR)
	$(CP) $(SOURCE_ROOT)/README $(SOURCE_ROOT)/COPYING $(PORTABLE_OUTPUT_DIR)
	$(CP) -r $(SOURCE_ROOT)/bin $(SOURCE_ROOT)/share $(SOURCE_ROOT)/src $(PORTABLE_OUTPUT_DIR)
	$(RM) -r $(PORTABLE_OUTPUT_DIR)/src/gpodder/qmlui
	$(RM) -r $(PORTABLE_OUTPUT_DIR)/share/gpodder/ui/qml
	$(RM) -r $(PORTABLE_OUTPUT_DIR)/share/applications
	$(RM) -r $(PORTABLE_OUTPUT_DIR)/share/dbus-1
	$(RM) -r $(PORTABLE_OUTPUT_DIR)/share/man
	find $(PORTABLE_OUTPUT_DIR) -name '*.pyc' -exec $(RM) {} +
	find $(PORTABLE_OUTPUT_DIR) -name '*.ui.h' -exec $(RM) {} +

$(PORTABLE_OUTPUT): $(PORTABLE_OUTPUT_DIR)
	zip -r $(PORTABLE_OUTPUT) $(PORTABLE_OUTPUT_DIR)

$(LAUNCHER_ROOT)/$(GPODDER_EXE):
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) $(GPODDER_EXE)

$(LAUNCHER_ROOT)/$(GPO_EXE):
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) $(GPO_EXE)

clean:
	$(RM) -r $(PORTABLE_OUTPUT_DIR)
	$(CROSS_MAKE) -C $(LAUNCHER_ROOT) distclean

distclean: clean
	$(RM) -r $(PORTABLE_OUTPUT)

.PHONY: all clean distclean $(PORTABLE_OUTPUT_DIR) $(LAUNCHER_ROOT)/$(GPODDER_EXE) $(LAUNCHER_ROOT)/$(GPO_EXE)
.DEFAULT: all
