#ifndef _GPODDER_H
#define _GPODDER_H

#define PROGNAME "gPodder"

#define BAILOUT(s) { \
    MessageBox(NULL, s, "Error launching " PROGNAME, MB_OK); \
    exit(1); \
}

#define DEBUG(a, b) { \
    MessageBox(NULL, a, b, MB_OK); \
}

#define GPODDER_REGISTRY_KEY \
    "Software\\gpodder.org\\gPodder"

#endif
