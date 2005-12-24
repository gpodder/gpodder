#!/usr/bin/env python

# tepache
# A code sketcher for python that uses pygtk, glade and SimpleGladeApp.py
# Copyright (C) 2004 Sandino Flores Moreno
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA


import os
import sys
import re
import codecs
import tokenize
import shutil
import time
import inspect
import optparse
import xml.sax
from xml.sax._exceptions import SAXParseException

if not hasattr(__builtins__, "set"):
    from sets import Set as set

__version__ = "1.1"
__autor__ = 'Sandino "tigrux" Flores-Moreno'
__WIN32__ = sys.platform.startswith("win")

gnuwin32_home = "http://gnuwin32.sourceforge.net/packages.html"
pywin32_home = "http://sourceforge.net/projects/pywin32"


Name_re = re.compile("(%s)" % tokenize.Name)
ClassName_re = re.compile("([a-zA-Z0-9]+)")
InstanceName_re = re.compile("([a-z])([A-Z])")
Comment_re = re.compile(r"#-- (%s)\.(%s) (\{|\})" % (2*(tokenize.Name,)))

def normalize_symbol(base):
    return "_".join(Name_re.findall(base))

def capitalize_symbol(base):
    base = normalize_symbol(base)
    base_pieces = [piece.capitalize() for piece in ClassName_re.findall(base)]
    return "".join(base_pieces)

def uncapitalize_symbol(base):
    def action(m):
    	groups = m.groups()
    	return "%s_%s" % (groups[0], groups[1].lower())
    base = normalize_symbol(base)
    base = base[0].lower() + base[1:]
    return InstanceName_re.sub(action, base)    

def printerr(s):
    print >> sys.stderr, str(s)


class NotGladeDocumentException(SAXParseException):

    def __init__(self, glade_writer):
        strerror = "Not a glade-2 document"
        SAXParseException.__init__(
            self, strerror, None,
            glade_writer.sax_parser)


class SimpleGladeCodeWriter(xml.sax.handler.ContentHandler):

    def __init__(self, glade_file):
        self.code = ""
        self.roots_list = []
        self.widgets_stack = []
        self.tags_stack = []
        self.creation_functions = []
        self.callbacks = []
        self.members = dict(inspect.getmembers(self))

        self.parent_is_creation_function = False
        self.parent_is_object = False
        self.parent_is_program_name = False
        self.requires_gnome = False

        self.glade_file = glade_file
        self.input_dir, self.input_file = os.path.split(glade_file)
        base = os.path.splitext(self.input_file)[0]
        self.gladep_file = os.path.join(self.input_dir, base) + ".gladep"
        self.module = normalize_symbol(base)
        self.output_file = os.path.join(self.input_dir, self.module) + ".py"

        self.sax_parser = xml.sax.make_parser()
        self.sax_parser.setFeature(xml.sax.handler.feature_external_ges, False)
        self.sax_parser.setContentHandler(self)

        self.data = {}
        self.data["glade"] = self.input_file
        self.data["module"] = self.output_file
        self.data["date"] = time.asctime()
        self.data["app_name"] = self.module.lower()
        self.data["app_version"] = "0.0.1"
        self.indent = 4 * " "

    def write(self, output_file=None):
        module_code = ""
        if output_file:
            self.data["module"] = self.output_file = output_file

        self.data["t"] = self.indent            
        if not self.parse():
            return False

        module_code += header_format % self.data
        if self.requires_gnome:
            module_code += import_gnome_format % self.data
        module_code += app_format % self.data
        module_code += self.code

        module_code += main_format % self.data
        if self.requires_gnome:
            module_code += gnome_init_format % self.data

        for root in self.roots_list:
            self.data["class"] = capitalize_symbol(root)
            self.data["instance"] = uncapitalize_symbol(root)
            module_code += instance_format % self.data

        self.data["root"] = uncapitalize_symbol(self.roots_list[0])
        module_code += run_format % self.data
        
        try:
            self.output = codecs.open(self.output_file, "w", "utf-8")
            self.output.write(module_code)
            self.output.close()
        except IOError, e:
            printerr(e)
            return False

        return True

    def parse(self):
        if os.path.isfile(self.gladep_file):
            try:
                gladep = open(self.gladep_file, "r")
                self.sax_parser.parse(gladep)
            except SAXParseException, e:
                printerr("Error parsing project file:")
                printerr(e)
            except IOError, e:
                printerr(e)

        try:
            glade = open(self.glade_file, "r")
            self.sax_parser.parse(glade)
        except SAXParseException, e:
            printerr("Error parsing document:")
            printerr(e)
            return False
        except IOError, e:
            printerr(e)
            return False

        return True

    def startElement(self, name, attrs):
        self.tags_stack.append(name)
        if self.parent_is_object:
            return
        handler = self.members.get("start_%s" % name)
        if callable(handler):
            handler(name, attrs)

    def endElement(self, name):
        handler = self.members.get("end_%s" % name)
        if callable(handler):
            handler(name)
        if not self.tags_stack:
            raise NotGladeDocumentException(self)
        self.tags_stack.pop()

    def characters(self, content):
        content = content.strip()
        name = self.tags_stack[-1]
        handler = self.members.get("characters_%s" % name)
        if callable(handler):
            handler(content)

    def characters_creation_function(self, content):
        if not self.widgets_stack:
            raise NotGladeDocumentException(self)
        handler = content
        if handler not in self.creation_functions:
            self.data["handler"] = handler
            self.code += creation_format % self.data
            self.creation_functions.append(handler)

    def characters_program_name(self, content):
        self.data["app_name"] = content

    def start_object(self, name, attrs):
        self.parent_is_object = True

    def end_object(self, name):
        self.parent_is_object = False

    def start_widget(self, name, attrs):
        widget_id = attrs.get("id")
        api_widget_id = widget_id.split(":")[-1]
        widget_class = attrs.get("class")
        if not widget_id or not widget_class:
            raise NotGladeDocumentException(self)
        if not self.widgets_stack:
            self.creation_functions = []
            self.callbacks = []
            class_name = capitalize_symbol(api_widget_id)
            self.data["class"] = class_name
            self.data["root"] = widget_id
            self.roots_list.append(api_widget_id)
            self.code += class_format % self.data
        self.widgets_stack.append(widget_id)

    def end_widget(self, name):
        if not self.widgets_stack:
            raise NotGladeDocumentException(self)
        self.widgets_stack.pop()

    def start_signal(self, name, attrs):
        if not self.widgets_stack:
            raise NotGladeDocumentException(self)
        widget = self.widgets_stack[-1]
        signal_object = attrs.get("object")
        if signal_object:
            return
        handler = attrs.get("handler")
        if not handler:
            raise NotGladeDocumentException(self)
        if handler.startswith("gtk_"):
            return
        signal = attrs.get("name")
        if not signal:
            raise NotGladeDocumentException(self)
        self.data["widget"] = widget
        self.data["signal"] = signal
        self.data["handler"]= handler
        if handler not in self.callbacks:
            self.code += callback_format % self.data
            self.callbacks.append(handler)

    def start_property(self, name, attrs):
        if not self.widgets_stack:
            raise NotGladeDocumentException(self)
        widget = self.widgets_stack[-1]
        prop_name = attrs.get("name")
        if not prop_name:
            raise NotGladeDocumentException(self)
        if prop_name == "creation_function":
            self.tags_stack.append("creation_function")

    def end_property(self, name):
        if self.tags_stack[-1] == "creation_function":
            self.tags_stack.pop()

    def start_requires(self, name, attrs):
        lib = attrs.get("lib")
        if lib == "gnome":
            self.requires_gnome = True

    def start_program_name(self, name, attrs):
        self.parent_is_program_name = True

    def end_program_name(self, name):
        self.parent_is_program_name = False

def get_callbacks_from_code(code_filename):
    class_opened_methods_l = []
    classes_l = []
    class_methods_d = {}

    for line in open(code_filename):
        found_all = Comment_re.findall(line)
        if found_all:
            (found,) = found_all
            class_method = found[0:2]
            curl = found[2]
            if curl == "{":
                class_opened_methods_l.append(class_method)
            elif curl == "}":
                if class_method in class_opened_methods_l:
                    class_s, method_s = class_method
                    if not class_s in classes_l:
                        classes_l.append(class_s)
                        class_methods_d[class_s] = set()
                    class_methods_d[class_s].add(method_s)

    classes_methods_l = [
        (class_s, class_methods_d[class_s]) for class_s in classes_l
    ]
    return classes_methods_l

def get_renamed_symbols(orig_callbacks, new_callbacks):
    renamed_symbols = {}
    callbacks_pairs = zip(orig_callbacks, new_callbacks)
    for orig_callback, new_callback in callbacks_pairs:
        orig_class, orig_methods = orig_callback
        new_class, new_methods = new_callback
        if orig_class != new_class:
            if orig_methods.issubset(new_methods):
                cap_orig_class = capitalize_symbol(orig_class)
                uncap_orig_class = uncapitalize_symbol(orig_class)

                cap_new_class = capitalize_symbol(new_class)
                uncap_new_class = uncapitalize_symbol(new_class)

                renamed_symbols[cap_orig_class] = cap_new_class
                renamed_symbols[uncap_orig_class] = uncap_new_class
    return renamed_symbols

def diff_apply_renamed_symbols(diff_file, renamed_widgets):
    def action(m):
        orig_symbol = m.group(0)
        if orig_symbol in renamed_widgets:
            renamed_symbol = renamed_widgets[orig_symbol]
            return renamed_symbol
        else:
            return orig_symbol
    diff_file_content = open(diff_file).read()
    new_diff_file_content = Name_re.sub(action, diff_file_content)
    open(diff_file, "w").write(new_diff_file_content)


def normalize_indentation(source_filename):
    source_data = open(source_filename).read()
    normalized_source_data = source_data.expandtabs(4)
    if normalized_source_data != source_data:
        print "Normalizing indentation of", source_filename
        open(source_filename, "w").write(normalized_source_data)


def get_binaries_path():
    binaries_path_list =  os.environ["PATH"].split(os.pathsep)
    if __WIN32__:
        try:
            import win32con
            import win32api
            import pywintypes
            gnu_path = ""
            try:
                winreg_key = win32con.HKEY_LOCAL_MACHINE
                winreg_subkey = "SOFTWARE\\GnuWin32"
                h = win32api.RegOpenKey(winreg_key, winreg_subkey)
                gnu_path = win32api.RegQueryValueEx(h, "InstallPath")[0]
                win32api.RegCloseKey(h)
                gnu_path_bin = os.path.join(gnu_path, "bin")
                binaries_path_list.insert(0, gnu_path_bin)
            except pywintypes.error, e:
                printerr("You haven't installed any GnuWin32 program.")
        except ImportError:
            printerr("I can't look for programs in the win32 registry")
            printerr("The pywin32 extension should be installed")
            printerr("Download it from %s\n" % pywin32_home)
    return binaries_path_list

def get_programs_paths(programs_list):
    if __WIN32__:
        exe_ext = ".exe"
    else:
        exe_ext = ""
    path_list =  get_binaries_path()
    programs_paths = [None,]*len(programs_list)
    for i,program in enumerate(programs_list):
        for path in path_list:
            program_path = os.path.join(path, program) + exe_ext
            if os.path.isfile(program_path):
                if " " in program_path:
                    program_path = '"%s"' % program_path
                programs_paths[i] = program_path
    return programs_paths

def get_required_programs():
    program_names = ["diff", "patch"]
    package_names = ["diffutils", "patch"]

    programs_paths = get_programs_paths(program_names)
    for i,program_path in enumerate(programs_paths):
        if not program_path:
            program, package = program_names[i], package_names[i]
            printerr("Required program %s could not be found" % program)
            printerr("Is the package %s installed?" % package)
            if __WIN32__:            
                printerr("Download it from %s" % gnuwin32_home)
            return None
    return programs_paths

def get_options_status():
    usage = "usage: %prog [options] [GLADE_FILE] [OUTPUT_FILE]"
    description = "write a sketch of python code from a glade file."
    status = True
    version = "1.0"
    parser = optparse.OptionParser(usage=usage, version=version,
                                      description=description)
    parser.add_option("-g", "--glade", dest="glade_file",
                      help="file to parse")
    parser.add_option("-o", "--output", dest="output_file",
                      help="file to write the sketch of the code")
    parser.add_option("-n", "--no-helper", dest="no_helper",
                      action="store_true",
                      help="Do not write the helper module")
    parser.add_option("-t", "--use-tabs", dest="use_tabs",
                      action="store_true",
                      help="\
Use tabs instead of 4 spaces for indenting. Discouraged according to PEP-8.")

    (options, args) = parser.parse_args()
    if not options.glade_file:
        if len(args) > 0:
            options.glade_file = args[0]
        else:
            status = False
            parser.print_help()
    if not options.output_file:
        if len(args) > 1:
            options.output_file = args[1]
    return options, status

def main():
    programs_paths = get_required_programs()
    if not programs_paths:
        return -1
    diff_bin, patch_bin = programs_paths

    options, status = get_options_status()
    if not status:
        return -1
        
    code_writer = SimpleGladeCodeWriter(options.glade_file)
    if not options.output_file:
        output_file = code_writer.output_file
    else:
        output_file = options.output_file
    output_file_orig = output_file + ".orig"
    output_file_bak = output_file + ".bak"
    short_f = os.path.basename(output_file)
    short_f_orig = short_f + ".orig"
    short_f_bak = short_f + ".bak"
    helper_module = os.path.join(code_writer.input_dir, "SimpleGladeApp.py")
    diff_file = "custom.diff"

    exists_output_file = os.path.exists(output_file)
    exists_output_file_orig = os.path.exists(output_file_orig)

    if not exists_output_file_orig and exists_output_file:
        printerr('File "%s" exists' % short_f)
        printerr('but "%s" does not.' % short_f_orig)
        printerr("That means your custom code would be overwritten.")
        printerr('Please manually remove "%s"' % short_f)
        printerr("from this directory.")
        printerr("Anyway, I\'ll create a backup for you in")
        printerr('"%s"' % short_f_bak)
        shutil.copy(output_file, output_file_bak)
        return -1
    if options.use_tabs:
        code_writer.indent = "\t"
    if exists_output_file_orig and exists_output_file:
        if not options.use_tabs:
            normalize_indentation(output_file_orig)
            normalize_indentation(output_file)
        diff_command = "%s -U1 %s %s > %s"
        diff_args = (diff_bin, output_file_orig, output_file, diff_file)
        os.system(diff_command % diff_args)
        shutil.copy(output_file, output_file_bak)
        if not code_writer.write(output_file):
            os.remove(diff_file)
            return -1
        orig_callbacks = get_callbacks_from_code(output_file_orig)
        callbacks = get_callbacks_from_code(output_file)
        renamed_symbols = get_renamed_symbols(orig_callbacks, callbacks)
        if renamed_symbols:
            diff_apply_renamed_symbols(diff_file, renamed_symbols)
        shutil.copy(output_file, output_file_orig)
        patch_command = "%s -fp0 < %s"
        patch_args = (patch_bin, diff_file) 
        if os.system(patch_command % patch_args):
            os.remove(diff_file)
            return -1
        os.remove(diff_file)
    else:
        if not code_writer.write(output_file):
            return -1
        shutil.copy(output_file, output_file_orig)

    os.chmod(output_file, 0755)
    if not options.no_helper and not os.path.isfile(helper_module):
            open(helper_module, "w").write(SimpleGladeApp_content)
    print "written file", output_file
    return 0

header_format = '''\
#!/usr/bin/env python
# -*- coding: UTF8 -*-

# Python module %(module)s
# Autogenerated from %(glade)s
# Generated on %(date)s

# Warning: Do not modify any context comment such as #--
# They are required to keep user's code

import os

import gtk
'''

app_format = '''\

from SimpleGladeApp import SimpleGladeApp
from SimpleGladeApp import bindtextdomain

app_name = "%(app_name)s"
app_version = "%(app_version)s"

glade_dir = ""
locale_dir = ""

bindtextdomain(app_name, locale_dir)

'''

import_gnome_format = '''\
import gnome
'''

class_format = '''\

class %(class)s(SimpleGladeApp):

%(t)sdef __init__(self, path="%(glade)s",
%(t)s             root="%(root)s",
%(t)s             domain=app_name, **kwargs):
%(t)s%(t)spath = os.path.join(glade_dir, path)
%(t)s%(t)sSimpleGladeApp.__init__(self, path, root, domain, **kwargs)

%(t)s#-- %(class)s.new {
%(t)sdef new(self):
%(t)s%(t)sprint "A new %%s has been created" %% self.__class__.__name__
%(t)s#-- %(class)s.new }

%(t)s#-- %(class)s custom methods {
%(t)s#   Write your own methods here
%(t)s#-- %(class)s custom methods }

'''

callback_format = '''\
%(t)s#-- %(class)s.%(handler)s {
%(t)sdef %(handler)s(self, widget, *args):
%(t)s%(t)sprint "%(handler)s called with self.%%s" %% widget.get_name()
%(t)s#-- %(class)s.%(handler)s }

'''

creation_format = '''\
%(t)s#-- %(class)s.%(handler)s {
%(t)sdef %(handler)s(self, str1, str2, int1, int2):
%(t)s%(t)swidget = gtk.Label("%(handler)s")
%(t)s%(t)swidget.show_all()
%(t)s%(t)sreturn widget
%(t)s#-- %(class)s.%(handler)s }

'''

main_format = '''\

#-- main {

def main():
'''

gnome_init_format = '''\
%(t)sgnome.program_init("%(app_name)s", "%(app_version)s")
'''

instance_format = '''\
%(t)s%(instance)s = %(class)s()
'''

run_format = '''\

%(t)s%(root)s.run()

if __name__ == "__main__":
%(t)smain()

#-- main }
'''

SimpleGladeApp_content = '''\
"""
 SimpleGladeApp.py
 Module that provides an object oriented abstraction to pygtk and libglade.
 Copyright (C) 2004 Sandino Flores Moreno
"""

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import sys
import re

import tokenize
import gtk
import gtk.glade
import weakref
import inspect

__version__ = "1.0"
__author__ = 'Sandino "tigrux" Flores-Moreno'

def bindtextdomain(app_name, locale_dir=None):
    """    
    Bind the domain represented by app_name to the locale directory locale_dir.
    It has the effect of loading translations, enabling applications for different
    languages.

    app_name:
        a domain to look for translations, tipically the name of an application.

    locale_dir:
        a directory with locales like locale_dir/lang_isocode/LC_MESSAGES/app_name.mo
        If omitted or None, then the current binding for app_name is used.
    """    
    try:
        import locale
        import gettext
        locale.setlocale(locale.LC_ALL, "")
        gtk.glade.bindtextdomain(app_name, locale_dir)
        gettext.install(app_name, locale_dir, unicode=1)
    except (IOError,locale.Error), e:
        print "Warning", app_name, e
        __builtins__.__dict__["_"] = lambda x : x


class SimpleGladeApp:

    def __init__(self, path, root=None, domain=None, **kwargs):
        """
        Load a glade file specified by glade_filename, using root as
        root widget and domain as the domain for translations.

        If it receives extra named arguments (argname=value), then they are used
        as attributes of the instance.

        path:
            path to a glade filename.
            If glade_filename cannot be found, then it will be searched in the
            same directory of the program (sys.argv[0])

        root:
            the name of the widget that is the root of the user interface,
            usually a window or dialog (a top level widget).
            If None or ommited, the full user interface is loaded.

        domain:
            A domain to use for loading translations.
            If None or ommited, no translation is loaded.

        **kwargs:
            a dictionary representing the named extra arguments.
            It is useful to set attributes of new instances, for example:
                glade_app = SimpleGladeApp("ui.glade", foo="some value", bar="another value")
            sets two attributes (foo and bar) to glade_app.
        """        
        if os.path.isfile(path):
            self.glade_path = path
        else:
            glade_dir = os.path.dirname( sys.argv[0] )
            self.glade_path = os.path.join(glade_dir, path)
        for key, value in kwargs.items():
            try:
                setattr(self, key, weakref.proxy(value) )
            except TypeError:
                setattr(self, key, value)
        self.glade = None
        self.install_custom_handler(self.custom_handler)
        self.glade = self.create_glade(self.glade_path, root, domain)
        if root:
            self.main_widget = self.get_widget(root)
        else:
            self.main_widget = None
        self.normalize_names()
        self.add_callbacks(self)
        self.new()

    def __repr__(self):
        class_name = self.__class__.__name__
        if self.main_widget:
            root = gtk.Widget.get_name(self.main_widget)
            repr = '%s(path="%s", root="%s")' % (class_name, self.glade_path, root)
        else:
            repr = '%s(path="%s")' % (class_name, self.glade_path)
        return repr

    def new(self):
        """
        Method called when the user interface is loaded and ready to be used.
        At this moment, the widgets are loaded and can be refered as self.widget_name
        """
        pass

    def add_callbacks(self, callbacks_proxy):
        """
        It uses the methods of callbacks_proxy as callbacks.
        The callbacks are specified by using:
            Properties window -> Signals tab
            in glade-2 (or any other gui designer like gazpacho).

        Methods of classes inheriting from SimpleGladeApp are used as
        callbacks automatically.

        callbacks_proxy:
            an instance with methods as code of callbacks.
            It means it has methods like on_button1_clicked, on_entry1_activate, etc.
        """        
        self.glade.signal_autoconnect(callbacks_proxy)

    def normalize_names(self):
        """
        It is internally used to normalize the name of the widgets.
        It means a widget named foo:vbox-dialog in glade
        is refered self.vbox_dialog in the code.

        It also sets a data "prefixes" with the list of
        prefixes a widget has for each widget.
        """
        for widget in self.get_widgets():
            widget_name = gtk.Widget.get_name(widget)
            prefixes_name_l = widget_name.split(":")
            prefixes = prefixes_name_l[ : -1]
            widget_api_name = prefixes_name_l[-1]
            widget_api_name = "_".join( re.findall(tokenize.Name, widget_api_name) )
            gtk.Widget.set_name(widget, widget_api_name)
            if hasattr(self, widget_api_name):
                raise AttributeError("instance %s already has an attribute %s" % (self,widget_api_name))
            else:
                setattr(self, widget_api_name, widget)
                if prefixes:
                    gtk.Widget.set_data(widget, "prefixes", prefixes)

    def add_prefix_actions(self, prefix_actions_proxy):
        """
        By using a gui designer (glade-2, gazpacho, etc)
        widgets can have a prefix in theirs names
        like foo:entry1 or foo:label3
        It means entry1 and label3 has a prefix action named foo.

        Then, prefix_actions_proxy must have a method named prefix_foo which
        is called everytime a widget with prefix foo is found, using the found widget
        as argument.

        prefix_actions_proxy:
            An instance with methods as prefix actions.
            It means it has methods like prefix_foo, prefix_bar, etc.
        """        
        prefix_s = "prefix_"
        prefix_pos = len(prefix_s)

        is_method = lambda t : callable( t[1] )
        is_prefix_action = lambda t : t[0].startswith(prefix_s)
        drop_prefix = lambda (k,w): (k[prefix_pos:],w)

        members_t = inspect.getmembers(prefix_actions_proxy)
        methods_t = filter(is_method, members_t)
        prefix_actions_t = filter(is_prefix_action, methods_t)
        prefix_actions_d = dict( map(drop_prefix, prefix_actions_t) )

        for widget in self.get_widgets():
            prefixes = gtk.Widget.get_data(widget, "prefixes")
            if prefixes:
                for prefix in prefixes:
                    if prefix in prefix_actions_d:
                        prefix_action = prefix_actions_d[prefix]
                        prefix_action(widget)

    def custom_handler(self,
            glade, function_name, widget_name,
            str1, str2, int1, int2):
        """
        Generic handler for creating custom widgets, internally used to
        enable custom widgets (custom widgets of glade).

        The custom widgets have a creation function specified in design time.
        Those creation functions are always called with str1,str2,int1,int2 as
        arguments, that are values specified in design time.

        Methods of classes inheriting from SimpleGladeApp are used as
        creation functions automatically.

        If a custom widget has create_foo as creation function, then the
        method named create_foo is called with str1,str2,int1,int2 as arguments.
        """
        try:
            handler = getattr(self, function_name)
            return handler(str1, str2, int1, int2)
        except AttributeError:
            return None

    def gtk_widget_show(self, widget, *args):
        """
        Predefined callback.
        The widget is showed.
        Equivalent to widget.show()
        """
        widget.show()

    def gtk_widget_hide(self, widget, *args):
        """
        Predefined callback.
        The widget is hidden.
        Equivalent to widget.hide()
        """
        widget.hide()

    def gtk_widget_grab_focus(self, widget, *args):
        """
        Predefined callback.
        The widget grabs the focus.
        Equivalent to widget.grab_focus()
        """
        widget.grab_focus()

    def gtk_widget_destroy(self, widget, *args):
        """
        Predefined callback.
        The widget is destroyed.
        Equivalent to widget.destroy()
        """
        widget.destroy()

    def gtk_window_activate_default(self, window, *args):
        """
        Predefined callback.
        The default widget of the window is activated.
        Equivalent to window.activate_default()
        """
        widget.activate_default()

    def gtk_true(self, *args):
        """
        Predefined callback.
        Equivalent to return True in a callback.
        Useful for stopping propagation of signals.
        """
        return True

    def gtk_false(self, *args):
        """
        Predefined callback.
        Equivalent to return False in a callback.
        """
        return False

    def gtk_main_quit(self, *args):
        """
        Predefined callback.
        Equivalent to self.quit()
        """
        self.quit()

    def main(self):
        """
        Starts the main loop of processing events.
        The default implementation calls gtk.main()

        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main()

        Do not directly call this method in your programs.
        Use the method run() instead.
        """
        gtk.main()

    def quit(self):
        """
        Quit processing events.
        The default implementation calls gtk.main_quit()
        
        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main_quit()
        """
        gtk.main_quit()

    def run(self):
        """
        Starts the main loop of processing events checking for Control-C.

        The default implementation checks wheter a Control-C is pressed,
        then calls on_keyboard_interrupt().

        Use this method for starting programs.
        """
        try:
            self.main()
        except KeyboardInterrupt:
            self.on_keyboard_interrupt()

    def on_keyboard_interrupt(self):
        """
        This method is called by the default implementation of run()
        after a program is finished by pressing Control-C.
        """
        pass

    def install_custom_handler(self, custom_handler):
        gtk.glade.set_custom_handler(custom_handler)

    def create_glade(self, glade_path, root, domain):
        return gtk.glade.XML(self.glade_path, root, domain)

    def get_widget(self, widget_name):
        return self.glade.get_widget(widget_name)

    def get_widgets(self):
        return self.glade.get_widget_prefix("")        
'''

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
