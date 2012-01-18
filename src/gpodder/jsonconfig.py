# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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
#  jsonconfig.py -- JSON Config Backend
#  Thomas Perl <thp@gpodder.org>   2012-01-18
#

import copy

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json


class JsonConfigSubtree(object):
    def __init__(self, parent, name):
        self._parent = parent
        self._name = name

    def __repr__(self):
        return '<Subtree %r of %r>' % (self._name, self._parent)

    def _attr(self, name):
        return '.'.join((self._name, name))

    def __getitem__(self, name):
        return self._parent._lookup(self._name).__getitem__(name)

    def __delitem__(self, name):
        self._parent._lookup(self._name).__delitem__(name)

    def __setitem__(self, name, value):
        self._parent._lookup(self._name).__setitem__(name, value)

    def __getattr__(self, name):
        if name == 'keys':
            # Kludge for using dict() on a JsonConfigSubtree
            return getattr(self._parent._lookup(self._name), name)

        return getattr(self._parent, self._attr(name))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._parent.__setattr__(self._attr(name), value)


class JsonConfig(object):
    _INDENT = 2

    def __init__(self, data=None, default=None, on_key_changed=None):
        self._default = default
        self._data = copy.deepcopy(self._default)
        self._on_key_changed = on_key_changed
        if data is not None:
            self._restore(data)

    def _restore(self, backup):
        self._data = json.loads(backup)
        # Add newly-added default configuration options
        self._merge_keys(self._default)

    def _merge_keys(self, merge_source):
        # Recurse into the data and add missing items
        work_queue = [(self._data, merge_source)]
        while work_queue:
            data, default = work_queue.pop()
            for key, value in default.iteritems():
                if key not in data:
                    # Copy defaults for missing key
                    data[key] = copy.deepcopy(value)
                elif isinstance(value, dict):
                    # Recurse into sub-dictionaries
                    work_queue.append((data[key], value))

    def __repr__(self):
        return json.dumps(self._data, indent=self._INDENT)

    def _lookup(self, name):
        return reduce(lambda d, k: d[k], name.split('.'), self._data)

    def __getattr__(self, name):
        try:
            value = self._lookup(name)
            if not isinstance(value, dict):
                return value
        except KeyError:
            pass

        return JsonConfigSubtree(self, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        attrs = name.split('.')
        target_dict = self._data

        while attrs:
            attr = attrs.pop(0)
            if not attrs:
                old_value = target_dict.get(attr, None)
                if old_value != value or attr not in target_dict:
                    target_dict[attr] = value
                    if self._on_key_changed is not None:
                        self._on_key_changed(name, old_value, value)
                break

            target = target_dict.get(attr, None)
            if target is None or not isinstance(target, dict):
                target_dict[attr] = target = {}
            target_dict = target

