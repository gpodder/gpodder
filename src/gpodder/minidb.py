#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

# gpodder.minidb - A simple SQLite store for Python objects
# Thomas Perl, 2010-01-28

# based on: "ORM wie eine Kirchenmaus - a very poor ORM implementation
#            by thp, 2009-11-29 (thp.io/about)"

# This module is also available separately at:
#    http://thp.io/2010/minidb/


# For Python 2.5, we need to request the "with" statement
from __future__ import with_statement

try:
    import sqlite3.dbapi2 as sqlite
except ImportError:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        raise Exception('Please install SQLite3 support.')


import threading

class Store(object):
    def __init__(self, filename=':memory:'):
        self.db = sqlite.connect(filename, check_same_thread=False)
        self.lock = threading.RLock()

    def _schema(self, class_):
        return class_.__name__, list(sorted(class_.__slots__))

    def _set(self, o, slot, value):
        # Set a slot on the given object to value, doing a cast if
        # necessary. The value None is special-cased and never cast.
        cls = o.__class__.__slots__[slot]
        if value is not None:
            if isinstance(value, unicode):
                value = value.decode('utf-8')
            value = cls(value)
        setattr(o, slot, value)

    def commit(self):
        with self.lock:
            self.db.commit()

    def close(self):
        with self.lock:
            self.db.execute('VACUUM')
            self.db.close()

    def _register(self, class_):
        with self.lock:
            table, slots = self._schema(class_)
            cur = self.db.execute('PRAGMA table_info(%s)' % table)
            available = cur.fetchall()

            if available:
                available = [row[1] for row in available]
                missing_slots = (s for s in slots if s not in available)
                for slot in missing_slots:
                    self.db.execute('ALTER TABLE %s ADD COLUMN %s TEXT' % (table,
                        slot))
            else:
                self.db.execute('CREATE TABLE %s (%s)' % (table,
                        ', '.join('%s TEXT'%s for s in slots)))

    def convert(self, v):
        if isinstance(v, unicode):
            return v
        elif isinstance(v, str):
            # XXX: Rewrite ^^^ as "isinstance(v, bytes)" in Python 3
            return v.decode('utf-8')
        else:
            return str(v)

    def update(self, o, **kwargs):
        self.remove(o)
        for k, v in kwargs.items():
            setattr(o, k, v)
        self.save(o)

    def save(self, o):
        if hasattr(o, '__iter__'):
            klass = None
            for child in o:
                if klass is None:
                    klass = child.__class__
                    self._register(klass)
                    table, slots = self._schema(klass)

                if not isinstance(child, klass):
                    raise ValueError('Only one type of object allowed')

                used = [s for s in slots if getattr(child, s, None) is not None]
                values = [self.convert(getattr(child, slot)) for slot in used]
                self.db.execute('INSERT INTO %s (%s) VALUES (%s)' % (table,
                    ', '.join(used), ', '.join('?'*len(used))), values)
            return

        with self.lock:
            self._register(o.__class__)
            table, slots = self._schema(o.__class__)

            values = [self.convert(getattr(o, slot)) for slot in slots]
            self.db.execute('INSERT INTO %s (%s) VALUES (%s)' % (table,
                ', '.join(slots), ', '.join('?'*len(slots))), values)

    def delete(self, class_, **kwargs):
        with self.lock:
            self._register(class_)
            table, slots = self._schema(class_)
            sql = 'DELETE FROM %s' % (table,)
            if kwargs:
                sql += ' WHERE %s' % (' AND '.join('%s=?' % k for k in kwargs))
            try:
                self.db.execute(sql, kwargs.values())
                return True
            except Exception, e:
                return False

    def remove(self, o):
        if hasattr(o, '__iter__'):
            for child in o:
                self.remove(child)
            return

        with self.lock:
            self._register(o.__class__)
            table, slots = self._schema(o.__class__)

            # Use "None" as wildcard selector in remove actions
            slots = [s for s in slots if getattr(o, s, None) is not None]

            values = [self.convert(getattr(o, slot)) for slot in slots]
            self.db.execute('DELETE FROM %s WHERE %s' % (table,
                ' AND '.join('%s=?'%s for s in slots)), values)

    def load(self, class_, **kwargs):
        with self.lock:
            self._register(class_)
            table, slots = self._schema(class_)
            sql = 'SELECT %s FROM %s' % (', '.join(slots), table)
            if kwargs:
                sql += ' WHERE %s' % (' AND '.join('%s=?' % k for k in kwargs))
            try:
                cur = self.db.execute(sql, kwargs.values())
            except Exception, e:
                raise
            def apply(row):
                o = class_.__new__(class_)
                for attr, value in zip(slots, row):
                    try:
                        self._set(o, attr, value)
                    except ValueError, ve:
                        return None
                return o
            return filter(lambda x: x is not None, [apply(row) for row in cur])

    def get(self, class_, **kwargs):
        result = self.load(class_, **kwargs)
        if result:
            return result[0]
        else:
            return None

if __name__ == '__main__':
    class Person(object):
        __slots__ = {'username': str, 'id': int}

        def __init__(self, username, id):
            self.username = username
            self.id = id

        def __repr__(self):
            return '<Person "%s" (%d)>' % (self.username, self.id)

    m = Store()
    m.save(Person('User %d' % x, x*20) for x in range(50))

    p = m.get(Person, id=200)
    print p
    m.remove(p)
    p = m.get(Person, id=200)

    # Remove some persons again (deletion by value!)
    m.remove(Person('User %d' % x, x*20) for x in range(40))

    class Person(object):
        __slots__ = {'username': str, 'id': int, 'mail': str}

        def __init__(self, username, id, mail):
            self.username = username
            self.id = id
            self.mail = mail

        def __repr__(self):
            return '<Person "%s" (%s)>' % (self.username, self.mail)

    # A schema update takes place here
    m.save(Person('User %d' % x, x*20, 'user@home.com') for x in range(50))
    print m.load(Person)

