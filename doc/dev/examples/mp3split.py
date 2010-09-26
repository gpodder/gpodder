#!/usr/bin/python
# Example hooks script for gPodder.
# To use, copy it as a Python script into ~/.config/gpodder/hooks/mp3split.py
# See the module "gpodder.hooks" for a description of when each hook
# gets called and what the parameters of each hook are.

import gpodder
import tempfile
import shutil
import subprocess
import os

from gpodder.liblogger import log

def mp3split(from_file, to_file):
    sandbox = tempfile.mkdtemp('', 'gpodder.mp3split')
    log("mp3split: sandbox is %s", sandbox)
    # http://docs.python.org/library/subprocess.html#subprocess-replacements
    # http://www.doughellmann.com/PyMOTW/subprocess/
    try:
        command = 'mp3splt -ft 10.00 -o "@f_@n" "%s" -d "%s"' % (from_file, sandbox)
        log("mp3split: Executing %s", command)
        p = subprocess.Popen(command, shell=True)
        # retcode[1] values:
        #  <0: error
        #   0: success, script handle the copy by hand(snif, progress bar is not used)
        retcode = os.waitpid(p.pid, 0)
        log("mp3split: Child with pid %s returned %s", retcode[0], retcode[1])
    except OSError, e:
        log("mp3split: Execution failed: %s", e)

    destination = os.path.dirname(to_file)
    log("mp3split: destination is %s", destination)
    shutil.rmtree(destination)
    shutil.copytree(sandbox, destination)
    shutil.rmtree(sandbox)

class gPodderHooks(object):
    def __init__(self):
        pass

    def on_podcast_updated(self, podcast):
        pass

    def on_podcast_save(self, podcast):
        pass

    def on_episode_save(self, episode):
        pass

    def on_file_copied_to_filesystem(self, mp3playerdevice, from_file, to_file):
        log(u'on_file_copied_to_filesystem(%s, %s)' % (from_file, to_file))
        mp3split(from_file, to_file)
