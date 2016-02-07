
/**
 * gPodder - A media aggregator and podcast client
 * Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
 *
 * gPodder is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * gPodder is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 **/


/**
 * gPodder for Windows
 * Thomas Perl <thp@gpodder.org>; 2011-11-06
 **/


#include <windows.h>
#include <shlobj.h>

#include <stdio.h>
#include <stdlib.h>
#include <shellapi.h>
#include <string.h>
#include <sys/stat.h>
#include <stdbool.h>

#include "gpodder.h"
#include "folderselector.h"

#if defined(GPODDER_GUI)
# define MAIN_MODULE "bin\\gpodder"
#else
# define MAIN_MODULE "bin\\gpo"
#endif

#define LOOKUP_FUNCTION(x) {x = GetProcAddress(python_dll, #x); \
    if(x == NULL) {BAILOUT("Cannot find function: " #x);}}


static char *
get_python_install_path()
{
    static char InstallPath[MAX_PATH];
    DWORD InstallPathSize = MAX_PATH;
    HKEY RegKey;
    char *result = NULL;

    /* Try to detect "just for me"-installed Python version (bug 1480) */
    if (RegOpenKeyEx(HKEY_CURRENT_USER,
            "Software\\Python\\PythonCore\\2.7\\InstallPath",
            0, KEY_READ, &RegKey) != ERROR_SUCCESS) {
        /* Try to detect "for all users" Python (bug 1480, comment 9) */
        if (RegOpenKeyEx(HKEY_LOCAL_MACHINE,
                "Software\\Python\\PythonCore\\2.7\\InstallPath",
                0, KEY_READ, &RegKey) != ERROR_SUCCESS) {
            return NULL;
        }
    }

    if (RegQueryValueEx(RegKey, NULL, NULL, NULL,
                InstallPath, &InstallPathSize) == ERROR_SUCCESS) {
        result = strdup(InstallPath);
    }

    RegCloseKey(RegKey);
    return result;
}

char *FindPythonDLL()
{
    char *path = get_python_install_path();
    static const char *python27_dll = "\\python27.dll";
    char *result = malloc(strlen(path) + strlen(python27_dll) + 1);
    sprintf(result, "%s%s", path, python27_dll);
    free(path);
    return result;
}

bool contains_system_dll(const char *path, const char *filename)
{
    bool result = false;
    struct stat st;

    char *fn = malloc(strlen(path) + 1 + strlen(filename) + 1);
    sprintf(fn, "%s\\%s", path, filename);
    if (stat(fn, &st) == 0) {
        result = true;
    }
    free(fn);

    return result;
}

char *clean_path_variable(const char *path)
{
    char *old_path = strdup(path);
    int length = strlen(path) + 1;
    char *new_path = (char *)malloc(length);
    memset(new_path, 0, length);

    char *tok = strtok(old_path, ";");
    while (tok != NULL) {
        // Only add the path component if it doesn't contain msvcr90.dll
        if (!contains_system_dll(tok, "msvcr90.dll")) {
            if (strlen(new_path) > 0) {
                strcat(new_path, ";");
            }

            strcat(new_path, tok);
        }

        tok = strtok(NULL, ";");
    }

    free(old_path);
    return new_path;
}

int main(int argc, char** argv)
{
    char path_env[MAX_PATH];
    char current_dir[MAX_PATH];
    char *endmarker = NULL;
    const char *target_folder = NULL;
    char tmp[MAX_PATH];
    int force_select = 0;
    int i;
    void *MainPy;
    void *GtkModule;
    int _argc = 1;
    char *_argv[] = { MAIN_MODULE };
    TCHAR gPodder_Home[MAX_PATH];
    TCHAR Temp_Download_Filename[MAX_PATH];

    HMODULE python_dll;
    FARPROC Py_Initialize;
    FARPROC PySys_SetArgvEx;
    FARPROC PyImport_ImportModule;
    FARPROC PyFile_FromString;
    FARPROC PyFile_AsFile;
    FARPROC PyRun_SimpleFile;
    FARPROC Py_Finalize;

#if defined(GPODDER_CLI)
    SetConsoleTitle(PROGNAME);
#endif

    for (i=1; i<argc; i++) {
        if (strcmp(argv[i], "--select-folder") == 0) {
            force_select = 1;
        }
    }

    DetermineHomeFolder(force_select);

    if (GetEnvironmentVariable("GPODDER_HOME",
            gPodder_Home, sizeof(gPodder_Home)) == 0) {
        BAILOUT("Cannot determine download folder (GPODDER_HOME). Exiting.");
    }
    CreateDirectory(gPodder_Home, NULL);

    /* Set current directory to directory of launcher */
    strncpy(current_dir, argv[0], MAX_PATH);
    endmarker = strrchr(current_dir, '\\');
    if (endmarker == NULL) {
        endmarker = strrchr(current_dir, '/');
    }
    if (endmarker != NULL) {
        *endmarker = '\0';
        /* We know the folder where the launcher sits - cd into it */
        if (SetCurrentDirectory(current_dir) == 0) {
            BAILOUT("Cannot set current directory.");
        }
    }

    /**
     * Workaround for error R6034 (need to do this before Python DLL
     * is loaded, otherwise the runtime error will still show up)
     **/
    char *new_path = clean_path_variable(getenv("PATH"));
    SetEnvironmentVariable("PATH", new_path);
    free(new_path);

    /**
     * Workaround import issues with Python 2.7.11.
     **/
    if (getenv("PYTHONHOME") == NULL) {
        char *python_home = get_python_install_path();
        if (python_home) {
            SetEnvironmentVariable("PYTHONHOME", python_home);
            free(python_home);
        }
    }

    /* Only load the Python DLL after we've set up the environment */
    python_dll = LoadLibrary("python27.dll");

    if (python_dll == NULL) {
        char *dll_path = FindPythonDLL();
        if (dll_path != NULL) {
            python_dll = LoadLibrary(dll_path);
            free(dll_path);
        }
    }

    if (python_dll == NULL) {
        MessageBox(NULL,
                   PROGNAME " requires Python 2.7.\n"
                   "See http://gpodder.org/dependencies",
                   "Python 2.7 installation not found",
                   MB_OK | MB_ICONQUESTION);
        return 1;
    }

    LOOKUP_FUNCTION(Py_Initialize);
    LOOKUP_FUNCTION(PySys_SetArgvEx);
    LOOKUP_FUNCTION(PyImport_ImportModule);
    LOOKUP_FUNCTION(PyFile_FromString);
    LOOKUP_FUNCTION(PyFile_AsFile);
    LOOKUP_FUNCTION(PyRun_SimpleFile);
    LOOKUP_FUNCTION(Py_Finalize);

    Py_Initialize();
    argv[0] = MAIN_MODULE;
    PySys_SetArgvEx(argc, argv, 0);

#if defined(GPODDER_GUI)
    /* Check for GTK, but not if we are running the CLI */
    GtkModule = (void*)PyImport_ImportModule("gtk");
    if (GtkModule == NULL) {
        MessageBox(NULL,
                   PROGNAME " requires PyGTK.\n"
                   "See http://gpodder.org/dependencies",
                   "PyGTK installation not found",
                   MB_OK | MB_ICONQUESTION);
        return 1;
    }
    // decref GtkModule
#endif

    // XXX: Test for feedparser, mygpoclient, dbus

    MainPy = (void*)PyFile_FromString(MAIN_MODULE, "r");
    if (MainPy == NULL) { BAILOUT("Cannot load main file") }
    if (PyRun_SimpleFile(PyFile_AsFile(MainPy), MAIN_MODULE) != 0) {
        BAILOUT("There was an error running " MAIN_MODULE " in Python.");
    }
    // decref MainPy
    Py_Finalize();

    return 0;
}

