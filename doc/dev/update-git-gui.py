#!/usr/bin/python
# A graphical way to "git pull" from the repository
# 2009-04-27 Thomas Perl <thp.io/about>

import gtk
import gobject
import subprocess
import time
import threading
import sys
import os

git_checkout_root = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..', '..'))

class GitPullWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_title('Git updater for gPodder')
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.connect('destroy', gtk.main_quit)

        self.text_buffer = gtk.TextBuffer()
        self.text_view = gtk.TextView(self.text_buffer)
        self.text_view.set_editable(False)
        
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.text_view)
        self.add(self.sw)
        self.vadj = self.sw.get_vadjustment()

        self.resize(700, 400)
        self.show_all()

        self.thread = threading.Thread(target=self.thread_code)
        self.thread.start()

    def add_text(self, text):
        self.text_buffer.insert(self.text_buffer.get_end_iter(), text)
    
    def thread_code(self):
        global git_checkout_root
        command_line = ['git', 'pull', '-v']
        gobject.idle_add(self.add_text, 'Using checkout root: %s\n' % git_checkout_root)
        gobject.idle_add(self.add_text, 'Calling: %s\n' % (' '.join(command_line)))
        process = subprocess.Popen(command_line,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=git_checkout_root)
        for line in process.stdout:
            gobject.idle_add(self.add_text, line)

        result = process.wait()
        if result == 0:
            gobject.idle_add(self.add_text, '\n\nFinished successfully. You can close this window now.')
        else:
            gobject.idle_add(self.add_text, '\n\nThere was an error while executing Git. Status: %d' % result)


if __name__ == '__main__':
    gobject.threads_init()
    GitPullWindow()
    gtk.main()

