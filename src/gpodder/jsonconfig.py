# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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
        return '<Subtree %r of JsonConfig>' % (self._name,)

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
        """
        Create a new JsonConfig object

        data: A JSON string that contains the data to load (optional)
        default: A dict that contains default config values (optional)
        on_key_changed: Callback when a value changes (optional)

        The signature of on_key_changed looks like this:

            func(name, old_value, new_value)

            name: The key name, e.g. "ui.gtk.show_toolbar"
            old_value: The old value, e.g. False
            new_value: The new value, e.g. True

        For newly-set keys, on_key_changed is also called. In this case,
        None will be the old_value:

        >>> def callback(*args): print 'callback:', args
        >>> c = JsonConfig(on_key_changed=callback)
        >>> c.a.b = 10
        callback: ('a.b', None, 10)
        >>> c.a.b = 11
        callback: ('a.b', 10, 11)
        >>> c.x.y.z = [1,2,3]
        callback: ('x.y.z', None, [1, 2, 3])
        >>> c.x.y.z = 42
        callback: ('x.y.z', [1, 2, 3], 42)

        Please note that dict-style access will not call on_key_changed:

        >>> def callback(*args): print 'callback:', args
        >>> c = JsonConfig(on_key_changed=callback)
        >>> c.a.b = 1        # This works as expected
        callback: ('a.b', None, 1)
        >>> c.a['c'] = 10    # This doesn't call on_key_changed!
        >>> del c.a['c']     # This also doesn't call on_key_changed!
        """
        self._default = default
        self._data = copy.deepcopy(self._default) or {}
        self._on_key_changed = on_key_changed
        if data is not None:
            self._restore(data)

    def _restore(self, backup):
        """
        Restore a previous state saved with repr()

        This function allows you to "snapshot" the current values of
        the configuration and reload them later on. Any missing
        default values will be added on top of the restored config.

        Returns True if new keys from the default config have been added,
        False if no keys have been added (backup contains all default keys)

        >>> c = JsonConfig()
        >>> c.a.b = 10
        >>> backup = repr(c)
        >>> print c.a.b
        10
        >>> c.a.b = 11
        >>> print c.a.b
        11
        >>> c._restore(backup)
        False
        >>> print c.a.b
        10
        """
        self._data = json.loads(backup)
        # Add newly-added default configuration options
        if self._default is not None:
            return self._merge_keys(self._default)

        return False

    def _merge_keys(self, merge_source):
        """Merge keys from merge_source into this config object

        Return True if new keys were merged, False otherwise
        """
        added_new_key = False
        # Recurse into the data and add missing items
        work_queue = [(self._data, merge_source)]
        while work_queue:
            data, default = work_queue.pop()
            for key, value in default.iteritems():
                if key not in data:
                    # Copy defaults for missing key
                    data[key] = copy.deepcopy(value)
                    added_new_key = True
                elif isinstance(value, dict):
                    # Recurse into sub-dictionaries
                    work_queue.append((data[key], value))
                elif type(value) != type(data[key]):
                    # Type mismatch of current value and default
                    if type(value) == int and type(data[key]) == float:
                        # Convert float to int if default value is int
                        data[key] = int(data[key])

        return added_new_key

    def __repr__(self):
        """
        >>> c = JsonConfig('{"a": 1}')
        >>> print c
        {
          "a": 1
        }
        """
        return json.dumps(self._data, indent=self._INDENT, sort_keys=True)

    def _lookup(self, name):
        return reduce(lambda d, k: d[k], name.split('.'), self._data)

    def _keys_iter(self):
        work_queue = []
        work_queue.append(([], self._data))
        while work_queue:
            path, data = work_queue.pop(0)

            if isinstance(data, dict):
                for key in sorted(data.keys()):
                    work_queue.append((path + [key], data[key]))
            else:
                yield '.'.join(path)

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

