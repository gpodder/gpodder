
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
 * gPodder Launcher for Win32
 * Set up environment variables and start the Python Interpreter
 * Thomas Perl <thp@gpodder.org>; 2009-04-29
 **/


#include <windows.h>

#include <stdlib.h>
#include <shellapi.h>
#include <string.h>

#include "gpodder.h"
#include "migrate.h"

#define MAIN_MODULE "gpodder.gtkui.win32"

int main(int argc, char** argv)
{
    char path_env[MAX_PATH];
    char current_dir[MAX_PATH];
    char *endmarker = NULL;
    int i;

    /* Start with the dirname of the executable */
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
        /* If possible, ask the user if (s)he wants to get portable */
        migrate_to_portable(current_dir);
    }

    if (GetEnvironmentVariable("PATH", path_env, MAX_PATH) == 0) {
        BAILOUT("Cannot get PATH environment variable.");
    }

    /* Add the "bin/" subfolder to the PATH variable */
    strncpy(current_dir, ".\\bin;", MAX_PATH);
    strncat(current_dir, path_env, MAX_PATH);

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

