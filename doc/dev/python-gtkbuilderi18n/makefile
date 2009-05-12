
# Dummy module to allow access to textdomain() and bindtextdomain() in Windows
# Thomas Perl <thpinfo.com>; 2009-05-12

MODULE = gtkbuilderi18n.so

OBJS += gtkbuilderi18n.o

CFLAGS += `python-config --cflags`
INCLUDES += `python-config --includes`
LDFLAGS += `python-config --libs`

$(MODULE): $(OBJS)
	$(CC) $< $(CFLAGS) -shared -fPIC $(LDFLAGS) -Wl,-soname,$@ -o $@

clean:
	rm -f $(OBJS) $(MODULE)

