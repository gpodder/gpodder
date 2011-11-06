
/**
 * gPodder - A media aggregator and podcast client
 * Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

#include <stdlib.h>
#include <shellapi.h>
#include <string.h>

#define PROGNAME "gPodder"

#define BAILOUT(s) { \
    MessageBox(NULL, s, "Error launching " PROGNAME, MB_OK); \
    exit(1); \
}

#if defined(GPODDER_GUI)
# define MAIN_MODULE "bin\\gpodder"
#else
# define MAIN_MODULE "bin\\gpo"
#endif

#define PYTHON_INSTALLER_FILE "python-2.7.2.msi"
#define PYTHON_INSTALLER_SIZE 15970304L
#define PYGTK_INSTALLER_FILE "pygtk-all-in-one-2.24.0.win32-py2.7.msi"
#define PYGTK_INSTALLER_SIZE 33583548L

#define PYTHON_INSTALLER_URL \
    "http://python.org/ftp/python/2.7.2/" \
    PYTHON_INSTALLER_FILE

#define PYGTK_INSTALLER_URL \
    "http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/" \
    PYGTK_INSTALLER_FILE

#define LOOKUP_FUNCTION(x) {x = GetProcAddress(python_dll, #x); \
    if(x == NULL) {BAILOUT("Cannot find function: " #x);}}

int main(int argc, char** argv)
{
    char path_env[MAX_PATH];
    char current_dir[MAX_PATH];
    char *endmarker = NULL;
    int i;
    void *MainPy;
    void *GtkModule;
    int _argc = 1;
    char *_argv[] = { MAIN_MODULE };
    TCHAR gPodder_Home[MAX_PATH];

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

    if (getenv("GPODDER_HOME") == NULL) {
        /* Get path to the "My Documents" folder */
        if (SHGetFolderPath(NULL,
                    CSIDL_PERSONAL | CSIDL_FLAG_CREATE,
                    NULL,
                    0,
                    gPodder_Home) != S_OK) {
            BAILOUT("Cannot determine your home directory (SHGetFolderPath).");
        }

        strncat(gPodder_Home, "\\gPodder", MAX_PATH);
        if (SetEnvironmentVariable("GPODDER_HOME", gPodder_Home) == 0) {
            BAILOUT("SetEnvironmentVariable for GPODDER_HOME failed.");
        }
    }

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

    /* Only load the Python DLL after we've set up the environment */
    python_dll = LoadLibrary("python27.dll");

    if (python_dll == NULL) {
        if (MessageBox(NULL,
                PROGNAME " requires Python 2.7.\n"
                "Do you want to install it now?",
                "Python 2.7 installation not found",
                MB_YESNO | MB_ICONQUESTION) == IDYES) {
            if (DownloadFile(PYTHON_INSTALLER_FILE,
                        PYTHON_INSTALLER_URL,
                        PYTHON_INSTALLER_SIZE) == PYTHON_INSTALLER_SIZE) {
                ShellExecute(NULL,
                        "open",
                        PYTHON_INSTALLER_FILE,
                        NULL,
                        NULL,
                        SW_SHOWNORMAL);
            }
        }

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
        if (MessageBox(NULL,
                PROGNAME " requires PyGTK.\n"
                "Do you want to install it now?",
                "PyGTK installation not found",
                MB_YESNO | MB_ICONQUESTION) == IDYES) {
            if (DownloadFile(PYGTK_INSTALLER_FILE,
                        PYGTK_INSTALLER_URL,
                        PYGTK_INSTALLER_SIZE) == PYGTK_INSTALLER_SIZE) {
                ShellExecute(NULL,
                        "open",
                        PYGTK_INSTALLER_FILE,
                        NULL,
                        NULL,
                        SW_SHOWNORMAL);
            }
        }

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

