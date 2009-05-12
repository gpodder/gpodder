
/**
 * This module is based on code from "libglade.override" in PyGTK.
 * Contact person for gtkbuilderi18n is Thomas Perl <thpinfo.com>.
 *
 * pygtk- Python bindings for the GTK toolkit.
 * Copyright (C) 1998-2003  James Henstridge
 *
 *   libglade.override: overrides for the gtk.glade module.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA
 **/

#include "Python.h"

#include <libintl.h>

#define DOCSTRING_BINDTEXTDOMAIN "bindtextdomain(domain, localedir=None)\n\nBind the domain to the locale directory localedir.\nIf localedir is omitted or None, then the current\nbinding for domain is returned."
#define DOCSTRING_TEXTDOMAIN "textdomain(domain=None)\n\nChange or query the current global domain.\nIf domain is None, then the current global domain\nis returned, otherwise the global domain is set\nto domain, which is returned."

static PyObject*
gtkbuilderi18n_bindtextdomain(PyObject *self, PyObject *args, PyObject *kwargs);

static PyObject*
gtkbuilderi18n_textdomain(PyObject *self, PyObject *args, PyObject *kwargs);

static PyMethodDef
methods[] = {
    { "bindtextdomain", gtkbuilderi18n_bindtextdomain, METH_KEYWORDS,
        DOCSTRING_BINDTEXTDOMAIN },
    { "textdomain", gtkbuilderi18n_textdomain, METH_KEYWORDS,
        DOCSTRING_TEXTDOMAIN },
    { NULL, NULL, 0, NULL },
};

PyMODINIT_FUNC
initgtkbuilderi18n(void)
{
    (void)Py_InitModule("gtkbuilderi18n", methods);
}

static PyObject*
gtkbuilderi18n_bindtextdomain(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "domainname", "dirname", NULL };
    char *domainname, *dirname = NULL, *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
               "s|s:gtkbuilderi18n.bindtextdomain", kwlist,
               &domainname, &dirname))
        return NULL;
    ret = bindtextdomain(domainname, dirname);
    if (!ret) {
        PyErr_SetString(PyExc_MemoryError, "Not enough memory available.");
        return NULL;
    }
#ifdef HAVE_BIND_TEXTDOMAIN_CODESET
    bind_textdomain_codeset(domainname, "UTF-8");
#endif
    return PyString_FromString(ret);
}

static PyObject *
gtkbuilderi18n_textdomain(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "domainname", NULL };
    char *domainname = NULL, *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
               "|s:gtkbuilderi18n.textdomain", kwlist,
               &domainname))
        return NULL;
    ret = textdomain(domainname);
    if (!ret) {
        PyErr_SetString(PyExc_MemoryError, "Not enough memory available.");
        return NULL;
    }
    return PyString_FromString(ret);
}



