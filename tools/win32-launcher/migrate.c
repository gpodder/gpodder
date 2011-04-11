
#include "gpodder.h"
#include "migrate.h"

#include <stdio.h>
#include <string.h>
#include <windows.h>
#include <shellapi.h>
#include "shlobj.h"

int move_data(const char* src, const char* src_child,
              const char* dst, const char* dst_child,
              const char* title)
{
    char from[MAX_PATH] = {0};
    char to[MAX_PATH] = {0};
    SHFILEOPSTRUCT file_op = {
        NULL, /* hwnd */
        FO_MOVE, /* wFunc */
        from, /* pFrom */
        to, /* pTo */
        FOF_SIMPLEPROGRESS, /* fFlags */
        0, /* fAnyOperationsAborted */
        0, /* hNameMappings */
        title, /* lpszProgressTitle */
    };

    strncat(from, src, MAX_PATH);
    strncat(from, src_child, MAX_PATH-strlen(from));

    strncat(to, dst, MAX_PATH);
    strncat(to, dst_child, MAX_PATH-strlen(to));

    SHFileOperation(&file_op);

    return file_op.fAnyOperationsAborted;
}



void migrate_to_portable(const char* dest_dir)
{
    char home_dir[MAX_PATH] = {0};
    char config_file[MAX_PATH] = {0};
    int answer = 0;
    FILE* fp = NULL;

    /* If your DONTASK_FILE exists, don't bother asking.. */
    if (GetFileAttributes(DONTASK_FILE) != INVALID_FILE_ATTRIBUTES) {
        return;
    }

    /* Determine $HOME for the current user */
    if (SHGetFolderPath(NULL, CSIDL_PROFILE, NULL, 0, home_dir) != S_OK) {
        BAILOUT("Cannot determine profile directory.");
    }

    /* Only offer move if the config file exists */
    strcpy(config_file, home_dir);
    strcat(config_file, SETTINGS_FROM);
    strcat(config_file, "\\gpodder.conf");
    if (GetFileAttributes(config_file) == INVALID_FILE_ATTRIBUTES) {
        return;
    }

    /* Ask the user if (s)he wants to migrate */
    answer = MessageBox(NULL,
            "Do you want to move your podcast data from your Windows "
            "profile\nfolder to the gPodder folder, so you can use it "
            "in \"portable mode\"?",
            "Migrate to portable " PROGNAME "?",
            MB_YESNOCANCEL);

    switch (answer) {
        case IDCANCEL:
            /* Cancel should exit the launcher */
            exit(0);
            break;
        case IDNO:
            /* Create the DONTASK_FILE and continue */
            fp = fopen(DONTASK_FILE, "w");
            fclose(fp);
            return;
            break;
        default:
            /* Otherwise continue below... */
            break;
    }

    /* Move the downloads from $HOME to $CWD */
    if (move_data(home_dir, DOWNLOADS_FROM,
                  dest_dir, DOWNLOADS_TO,
                  "Moving downloaded episodes") != 0) {
        BAILOUT("Error while moving downloaded episodes.");
    }

    /* Move the settings from $HOME to $CWD */
    if (move_data(home_dir, SETTINGS_FROM,
                  dest_dir, SETTINGS_TO,
                  "Moving database and config") != 0) {
        BAILOUT("Error while moving database and config (only downloads were moved).");
    }

}

