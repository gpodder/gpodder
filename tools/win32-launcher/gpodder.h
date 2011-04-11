#ifndef _GPODDER_GPODDER_H
#define _GPODDER_GPODDER_H

#define PROGNAME "gPodder"

#define BAILOUT(s) { \
    MessageBox(NULL, s, "Error launching " PROGNAME, MB_OK); \
    exit(1); \
}

#endif

