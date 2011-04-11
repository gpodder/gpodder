#ifndef _GPODDER_MIGRATE_H
#define _GPODDER_MIGRATE_H

#define DOWNLOADS_FROM "\\gpodder-downloads"
#define DOWNLOADS_TO "\\downloads"
#define SETTINGS_FROM "\\.config\\gpodder"
#define SETTINGS_TO "\\config"
#define DONTASK_FILE "nonportable.ini"

void migrate_to_portable(const char* dest_dir);

#endif

