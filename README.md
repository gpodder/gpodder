          ___         _    _           ____
     __ _| _ \___  __| |__| |___ _ _  |__ /
    / _` |  _/ _ \/ _` / _` / -_) '_|  |_ \
    \__, |_| \___/\__,_\__,_\___|_|   |___/
    |___/
            Media aggregator and podcast client
___

Copyright  2005-2022 The gPodder Team


## License

gPodder is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

gPodder is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

## Dependencies

- [Python 3.7](http://python.org/) or newer
- [Podcastparser](http://gpodder.org/podcastparser/) 0.6.0 or newer
- [mygpoclient](http://gpodder.org/mygpoclient/) 1.7 or newer
- [requests](https://requests.readthedocs.io) 2.24.0 or newer
- Python D-Bus bindings

As an alternative to python-dbus on Mac OS X and Windows, you can use
the dummy (no-op) D-Bus module provided in "tools/fake-dbus-module/".

For quick testing, see [Run from Git](https://gpodder.github.io/docs/run-from-git.html)
to install dependencies.


### GTK3 UI - Additional Dependencies

- [PyGObject](https://wiki.gnome.org/PyGObject) 3.22.0 or newer
- [GTK+3](https://www.gtk.org/) 3.16 or newer


### Optional Dependencies

- Bluetooth file sending: gnome-obex-send or bluetooth-sendto
- Size detection on Windows: PyWin32
- Native OS X support: ige-mac-integration
- MP3 Player Sync Support: python-eyed3 (0.7 or newer)
- iPod Sync Support: libgpod (tested with 0.8.3)
- Clickable links in GTK UI show notes: html5lib
- HTML show notes: WebKit2 gobject bindings
    (webkit2gtk, webkitgtk4 or gir1.2-webkit2-4.0 packages).
- Better Youtube support (> 15 entries in feeds, download audio-only): youtube_dl or yt-dlp


### Build Dependencies

- help2man
- intltool


### Test Dependencies

- python-minimock
- pytest
- pytest-httpserver
- pytest-cov
- desktop-file-utils

## Testing

To run tests, use...

    make unittest

To set a specific python binary set PYTHON:

    PYTHON=python3 make unittest

Tests in gPodder are written in two different ways:

- [doctests](http://docs.python.org/3/library/doctest.html)
- [unittests](http://docs.python.org/3/library/unittest.html)

If you want to add doctests, simply write the doctest and make sure that
the module appears after `--doctest-modules` in `pytest.ini`. If you
add tests to any module in `src/gpodder` you have nothing to do.

If you want to add unit tests for a specific module (ex: gpodder.model),
you should add the tests as gpodder.test.model, or in other words:

    The file:       src/gpodder/model.py
    is tested by:   src/gpodder/test/model.py

After you've added the test, make sure that the module appears in
"test_modules" in src/gpodder/unittests.py - for the example above, the
unittests in src/gpodder/test/model.py are added as 'model'. For unit
tests, coverage reporting happens for the tested module (that's why the
test module name should mirror the module to be tested).


## Running and Installation

To run gPodder from source, use..

    bin/gpodder              # for the Gtk+ UI
    bin/gpo                  # for the command-line interface

To install gPodder system-wide, use `make install`. By default, this
will install *all* UIs and all translations. The following environment
variables are processed by setup.py:

    LINGUAS                  space-separated list of languages to install
    GPODDER_INSTALL_UIS      space-separated list of UIs to install
    GPODDER_MANPATH_NO_SHARE if set, install manpages to $PREFIX/man/man1

See setup.py for a list of recognized UIs.

Example: Install the CLI and Gtk UI with German and Dutch translations:

    export LINGUAS="de nl"
    export GPODDER_INSTALL_UIS="cli gtk"
    make install

The "make install" target also supports DESTDIR and PREFIX for installing
into an alternative root (default /) and prefix (default /usr):

    make install DESTDIR=tmp/ PREFIX=/usr/local/

[*Debian*](https://wiki.debian.org/Python#Deviations_from_upstream) and *Ubuntu* use `dist-packages`
instead of `site-packages` for third party installs, so you'll want something like:

    sudo python3 setup.py install --root / --prefix /usr/local --optimize=1 --install-lib=/usr/local/lib/python3.10/dist-packages

In fact, first try running `python -c "import sys; print(sys.path)"` to check what is the exact path.
It depends on your version of python.

## Portable Mode / Roaming Profiles

The run-time environment variable GPODDER_HOME is used to set
the location for storing the database and downloaded files.

This can be used for multiple configurations or to store the
download directory directly on a MP3 player or USB disk:

    export GPODDER_HOME=/media/usbdisk/gpodder-data/


## OS X Specific Notes

- default GPODDER_HOME="$HOME/Library/Application Support/gPodder"
- default GPODDER_DOWNLOAD_DIR="$HOME/Library/Application Support/gPodder/download"

These settings may be modified by editing the following file of the .app :

    /Applications/gPodder.app/Contents/MacOSX/_launcher

Add and edit the following lines to alter the launch environment on OS X :

    export GPODDER_HOME="$HOME/Library/Application Support/gPodder"
    export GPODDER_DOWNLOAD_DIR="$HOME/Library/Application Support/gPodder/download"


##  Changing the Download Directory

The run-time environment variable GPODDER_DOWNLOAD_DIR is used to
set the location for storing the downloads only (independent of the
data directory GPODDER_HOME):

    export GPODDER_DOWNLOAD_DIR=/media/BigDisk/Podcasts/

In this case, the database and settings will be stored in the default
location, with the downloads stored in /media/BigDisk/Podcasts/.

Another example would be to set both environment variables:

    export GPODDER_HOME=~/.config/gpodder/
    export GPODDER_DOWNLOAD_DIR=~/Podcasts/

This will store the database and settings files in ~/.config/gpodder/
and the downloads in ~/Podcasts/. If GPODDER_DOWNLOAD_DIR is not set,
$GPODDER_HOME/Downloads/ will be used if it is set.


## Logging

By default, gPodder writes log files to $GPODDER_HOME/Logs/ and removes
them after a certain amount of times. To avoid this behavior, you can set
the environment variable GPODDER_WRITE_LOGS to "no", e.g:

    export GPODDER_WRITE_LOGS=no


## Extensions

Extensions are normally loaded from gPodder's "extensions/" folder (in
share/gpodder/extensions/) and from $GPODDER_HOME/Extensions/ - you can
override this by setting an environment variable:

    export GPODDER_EXTENSIONS="/path/to/extension1.py extension2.py"

In addition to that, if you want to disable loading of all extensions,
you can do this by setting the following environment variable to a non-
empty value:

    export GPODDER_DISABLE_EXTENSIONS=yes

If you want to report a bug, please try to disable all extensions and
check if the bug still appears to see if an extension causes the bug.


## More Information

- Homepage:                         http://gpodder.org/
- Bug tracker:                      https://github.com/gpodder/gpodder/issues
- Mailing list:                     http://freelists.org/list/gpodder
- IRC channel:                      #gpodder on irc.libera.chat
