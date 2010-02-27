''' Dbm based on sqlite -- Needed to support shelves

Issues:

    # ??? how to coordinate with whichdb
    # ??? Any difference between blobs and text
    # ??? does default encoding affect str-->bytes or PySqlite3 always use UTF-8
    # ??? what is the correct isolation mode

'''

__all__ = ['error', 'open']

import sqlite3
from UserDict import DictMixin
import collections
from operator import itemgetter
import shelve

error = sqlite3.DatabaseError

class SQLhash(object, DictMixin):
    def __init__(self, filename=':memory:', flags='r', mode=None,
                 tablename='shelf'):
        # XXX add flag/mode handling
        #   c -- create if it doesn't exist
        #   n -- new empty
        #   w -- open existing
        #   r -- readonly

        self.tablename = tablename

        MAKE_SHELF = 'CREATE TABLE IF NOT EXISTS %s (key TEXT PRIMARY KEY, value TEXT NOT NULL)' % self.tablename
        self.conn = sqlite3.connect(filename)
        self.conn.text_factory = str
        self.conn.execute(MAKE_SHELF)
        self.conn.commit()

    def __len__(self):
        GET_LEN = 'SELECT COUNT(*) FROM %s' % self.tablename
        return self.conn.execute(GET_LEN).fetchone()[0]

    def __bool__(self):
        # returns None if count is zero
        GET_BOOL = 'SELECT MAX(ROWID) FROM %s' % self.tablename
        return self.conn.execute(GET_BOOL).fetchone()[0] is not None

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def __iter__(self):
        return self.iterkeys()

    def iterkeys(self):
        GET_KEYS = 'SELECT key FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_KEYS, (0,)))

    def itervalues(self):
        GET_VALUES = 'SELECT value FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_VALUES, (0,)))

    def iteritems(self):
        GET_ITEMS = 'SELECT key, value FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_ITEMS, (0, 1)))

    def __contains__(self, key):
        HAS_ITEM = 'SELECT 1 FROM %s WHERE key = ?' % self.tablename
        return self.conn.execute(HAS_ITEM, (key,)).fetchone() is not None

    def __getitem__(self, key):
        GET_ITEM = 'SELECT value FROM %s WHERE key = ?' % self.tablename
        item = self.conn.execute(GET_ITEM, (key,)).fetchone()
        if item is None:
            raise KeyError(key)

        return item[0]

    def __setitem__(self, key, value):       
        ADD_ITEM = 'REPLACE INTO %s (key, value) VALUES (?,?)' % self.tablename
        self.conn.execute(ADD_ITEM, (key, value))
        #self.conn.commit()

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        DEL_ITEM = 'DELETE FROM %s WHERE key = ?' % self.tablename
        self.conn.execute(DEL_ITEM, (key,))
        #self.conn.commit()

    def update(self, items=(), **kwds):
        try:
            items = items.items()
        except AttributeError:
            pass

        UPDATE_ITEMS = 'REPLACE INTO %s (key, value) VALUES (?, ?)' % \
                       self.tablename

        self.conn.executemany(UPDATE_ITEMS, items)
        self.conn.commit()
        if kwds:
            self.update(kwds)

    def clear(self):        
        CLEAR_ALL = 'DELETE FROM %s; VACUUM;' % self.tablename
        self.conn.executescript(CLEAR_ALL)
        self.conn.commit()

    def sync(self):
        if self.conn is not None:    
            self.conn.commit()

    def close(self):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def __del__(self):
        self.close()

def open(file=None, *args):
    if file is not None:
        return SQLhash(file)
    return SQLhash()

def open_shelf(file=None, *args):
    _db = open(file, *args)
    return shelve.Shelf(_db)

class SQLHashIterator(object):
    def __init__(self, conn, stmt, indices):
        c = conn.cursor()
        c.execute(stmt)
        
        self.iter = iter(c)
        self.getter = itemgetter(*indices)

    def __iter__(self):
        return self

    def next(self):
        return self.getter(self.iter.next())

if __name__ in '__main___':
    for d in SQLhash(), SQLhash('example'):
        list(d)
        print(list(d), "start")
        d['abc'] = 'lmno'
        print(d['abc'])    
        d['abc'] = 'rsvp'
        d['xyz'] = 'pdq'
        print(d.items())
        print(d.values())
        print('***', d.keys())
        print(list(d), 'list')
        d.update(p='x', q='y', r='z')
        print(d.items())
        
        del d['abc']
        try:
            print(d['abc'])
        except KeyError:
            pass
        else:
            raise Exception('oh noooo!')
        
        try:
            del d['abc']
        except KeyError:
            pass
        else:
            raise Exception('drat!')

        print(list(d))
        print(bool(d), True)        
        d.clear()
        print(bool(d), False)
        print(list(d))
        d.update(p='x', q='y', r='z')
        print(list(d))
        d['xyz'] = 'pdq'

        print()
        d.close()
