
#include "gpodder.h"
#include "folderselector.h"

#include <windows.h>
#include <shlobj.h>
#include <shellapi.h>


/* Private function declarations */

void
UseFolderSelector();

int
FolderExists(const char *folder);

void
UseFolder(const char *folder);

void
SaveFolder(const char *folder);

const char *
RegistryFolder();

const char *
DefaultFolder();

int
AskUserFolder(const char *folder);



void
DetermineHomeFolder(int force_select)
{
    if (force_select) {
        /* Forced selection of (new) download folder */
        UseFolderSelector();
        return;
    }

    if (getenv("GPODDER_HOME") != NULL) {
        /* GPODDER_HOME already set - don't modify */
        return;
    }

    if (FolderExists(RegistryFolder())) {
        /* Use folder in registry */
        UseFolder(RegistryFolder());
        return;
    }

    if (FolderExists(DefaultFolder())) {
        /* Save default in registry and use it */
        SaveFolder(DefaultFolder());
        UseFolder(DefaultFolder());
        return;
    }

    if (AskUserFolder(DefaultFolder())) {
        /* User wants to use the default folder */
        SaveFolder(DefaultFolder());
        UseFolder(DefaultFolder());
        return;
    }

    /* If everything else fails, use folder selector */
    UseFolderSelector();
}


void
UseFolderSelector()
{
    BROWSEINFO browseInfo = {
        0, /* hwndOwner */
        NULL, /* pidlRoot */
        NULL, /* pszDisplayName */
        "Select the data folder where gPodder will "
        "store the database and downloaded episodes:", /* lpszTitle */
        BIF_USENEWUI | BIF_RETURNONLYFSDIRS, /* ulFlags */
        NULL, /* lpfn */
        0, /* lParam */
        0, /* iImage */
    };
    LPITEMIDLIST pidList;
    static char path[MAX_PATH];

    pidList = SHBrowseForFolder(&browseInfo);
    if (pidList == NULL) {
        /* User clicked on "Cancel" */
        exit(2);
    }

    memset(path, 0, sizeof(path));
    if (!SHGetPathFromIDList(pidList, path)) {
        BAILOUT("Could not determine filesystem path from selection.");
    }

    CoTaskMemFree(pidList);

    SaveFolder(path);
    UseFolder(path);
}

int
FolderExists(const char *folder)
{
    DWORD attrs;

    if (folder == NULL) {
        return 0;
    }

    attrs = GetFileAttributes(folder);
    return ((attrs != INVALID_FILE_ATTRIBUTES) &&
            (attrs & FILE_ATTRIBUTE_DIRECTORY));
}

void
UseFolder(const char *folder)
{
    if (folder == NULL) {
        BAILOUT("Folder is NULL in UseFolder(). Exiting.");
    }

    if (SetEnvironmentVariable("GPODDER_HOME", folder) == 0) {
        BAILOUT("SetEnvironmentVariable for GPODDER_HOME failed.");
    }
}

void
SaveFolder(const char *folder)
{
    HKEY regKey;

    if (folder == NULL) {
        BAILOUT("Folder is NULL in SaveFolder(). Exiting.");
    }

    if (RegCreateKey(HKEY_CURRENT_USER, GPODDER_REGISTRY_KEY,
            &regKey) != ERROR_SUCCESS) {
        BAILOUT("Cannot create registry key:\n\n"
                "HKEY_CURRENT_USER\\" GPODDER_REGISTRY_KEY);
    }

    if (RegSetValueEx(regKey,
            "GPODDER_HOME",
            0,
            REG_SZ,
            folder,
            strlen(folder)+1) != ERROR_SUCCESS) {
        BAILOUT("Cannot set value in registry:\n\n"
                "HKEY_CURRENT_USER\\" GPODDER_REGISTRY_KEY);
    }

    RegCloseKey(regKey);
}

const char *
RegistryFolder()
{
    static char folder[MAX_PATH] = {0};
    DWORD folderSize = MAX_PATH;
    HKEY regKey;
    char *result = NULL;

    if (strlen(folder)) {
        return folder;
    }

    if (RegOpenKeyEx(HKEY_CURRENT_USER, GPODDER_REGISTRY_KEY,
            0, KEY_READ, &regKey) != ERROR_SUCCESS) {
        return NULL;
    }

    if (RegQueryValueEx(regKey, "GPODDER_HOME", NULL, NULL,
            folder, &folderSize) == ERROR_SUCCESS) {
        result = folder;
    }

    RegCloseKey(regKey);

    return result;
}

const char *
DefaultFolder()
{
    static char defaultFolder[MAX_PATH] = {0};

    if (!strlen(defaultFolder)) {
        if (SHGetFolderPath(NULL,
                    CSIDL_PERSONAL | CSIDL_FLAG_CREATE,
                    NULL,
                    0,
                    defaultFolder) != S_OK) {
            BAILOUT("Cannot determine your home directory (SHGetFolderPath).");
        }
        strncat(defaultFolder, "\\gPodder\\", MAX_PATH);
    }

    return defaultFolder;
}

int
AskUserFolder(const char *folder)
{
    char tmp[MAX_PATH+100];

    if (folder == NULL) return 0;

    strcpy(tmp, PROGNAME " requires a download folder.\n"
            "Use the default download folder?\n\n");
    strcat(tmp, folder);

    return (MessageBox(NULL, tmp, "No download folder selected",
            MB_YESNO | MB_ICONQUESTION) == IDYES);
}

