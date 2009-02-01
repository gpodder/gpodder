#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  my.py -- "my gPodder" service client
#  Thomas Perl <thp@gpodder.org>   2008-12-08
#


########################################################################
# Based on upload_test.py
# Copyright Michael Foord, 2004 & 2005.
# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/documents/BSD-LICENSE.txt
# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# E-mail fuzzyman@voidspace.org.uk
########################################################################

import urllib2
import mimetypes
import mimetools
import webbrowser

def encode_multipart_formdata(fields, files, BOUNDARY = '-----'+mimetools.choose_boundary()+'-----'):
    """ Encodes fields and files for uploading.
    fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files.
    Return (content_type, body) ready for urllib2.Request instance
    You can optionally pass in a boundary string to use or we'll let mimetools provide one.
    """
    CRLF = '\r\n'
    L = []
    if isinstance(fields, dict):
        fields = fields.items()
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        filetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % filetype)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def build_request(theurl, fields, files, txheaders=None):
    """Given the fields to set and the files to encode it returns a fully formed urllib2.Request object.
    You can optionally pass in additional headers to encode into the opject. (Content-type and Content-length will be overridden if they are set).
    fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    if not txheaders: txheaders = {}
    txheaders['Content-type'] = content_type
    txheaders['Content-length'] = str(len(body))
    return urllib2.Request(theurl, body, txheaders)


class MygPodderClient(object):
    WEBSERVICE = 'http://my.gpodder.org'

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def download_subscriptions(self):
        theurl = self.WEBSERVICE+"/getlist"
        args = {'username': self.username, 'password': self.password}
        args = '&'.join(('%s=%s' % a for a in args.items()))
        url = theurl + '?' + args
        opml_data = urllib2.urlopen(url).read()
        return opml_data

    def upload_subscriptions(self, filename):
        theurl = self.WEBSERVICE+'/upload'
        action = 'update-subscriptions'
        fields = {'username': self.username, 'password': self.password, 'action': 'update-subscriptions', 'protocol': '0'}
        opml_file = ('opml', 'subscriptions.opml', open(filename).read())

        result = urllib2.urlopen(build_request(theurl, fields, [opml_file])).read()
        messages = []

        success = False

        if '@GOTOMYGPODDER' in result:
            webbrowser.open(self.WEBSERVICE, new=1)
            messages.append(_('Please have a look at the website for more information.'))

        if '@SUCCESS' in result:
            messages.append(_('Subscriptions uploaded.'))
            success = True
        elif '@AUTHFAIL' in result:
            messages.append(_('Authentication failed.'))
        elif '@PROTOERROR' in result:
            messages.append(_('Protocol error.'))
        else:
            messages.append(_('Unknown response.'))

        return success, messages

