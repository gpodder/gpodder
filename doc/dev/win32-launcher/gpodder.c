
/**
 * gPodder - A media aggregator and podcast client
 * Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
 * gPodder Launcher for Win32
 * Set up environment variables and start the Python Interpreter
 * Thomas Perl <thpinfo.com>; 2009-04-29
 **/


#include <windows.h>

#include <stdlib.h>
#include <shellapi.h>
#include <string.h>

#define MAXPATH 8192
#define PROGNAME "gPodder"
#define MAIN_MODULE "gpodder.launcher"

#define BAILOUT(s) { \
    MessageBox(NULL, s, "Error launching " PROGNAME, MB_OK); \
    exit(1); \
}

int main(int argc, char** argv)
{
    char path_env[MAXPATH];
    char current_dir[MAXPATH];
    char *endmarker = NULL;
    int i;

    /* Start with the dirname of the executable */
    strncpy(current_dir, argv[0], MAXPATH);
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
    
    if (GetEnvironmentVariable("PATH", path_env, MAXPATH) == 0) {
        BAILOUT("Cannot get PATH environment variable.");
    }

    /* Add the "bin/" subfolder to the PATH variable */
    strncpy(current_dir, ".\\bin;", MAXPATH);
    strncat(current_dir, path_env, MAXPATH);

    if (SetEnvironmentVariable("PATH", current_dir) == 0) {
        BAILOUT("Cannot set PATH environment variable.");
    }

    /* Start the main module in the Python interpreter (pythonw.exe) */
    if ((int)ShellExecute(NULL,
            "open",
            "pythonw.exe",
            "-m " MAIN_MODULE,
            NULL,
            SW_SHOWDEFAULT) < 32) {
        BAILOUT("Error while executing the Python interpreter.");
    }

    return 0;
}

