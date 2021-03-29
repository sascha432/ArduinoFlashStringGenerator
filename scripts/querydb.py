#
# Author: sascha_lammers@gmx.de
#

import argparse
import json
import sys
import pickle
import fnmatch
from os import path
import os
from pprint import pprint
from generator import FileWrapper, DefinitionType, DatabaseOutputHelpers

class Database(object):
    def __init__(self, data):
        self.source_locations = 0
        self.static_count = 0
        self._unique = {}
        self._targets = data['targets']
        self._defined = data['defined']
        self._items = data['items']
        self._values = {}
        for items in self._items.values():
            self.source_locations += len(items)
            for item in items.values():
                if not item.name in self._values:
                    self._values[item.name] = None
                if item['own_value']!=None:
                    if self._values[item.name]!=self._values[item.name]:
                        raise RuntimeError('value for %s changed' % item.name)
                    self._values[item.name] = item['own_value']
                if item['type']==DefinitionType.DEFINE:
                    self.static_count += 1
                if not item.name in self._unique:
                    self._unique[item.name] = {}
                if item.index in self._unique[item.name]:
                    raise RuntimeError('index %s duplicate' % item.index)
                self._unique[item.name][item.index] = item

    @property
    def item_count(self):
        return len(self._unique)

    @property
    def values_count(self):
        return sum([(val!=None and 1 or 0) for val in self._values.values()])

    def query(self, query):
        if query.startswith('SPGM_'):
            query = query[5:]
        result = {
            'items': {},
            'values': {},
            'locations': {}
        }
        for items in self._items.values():
            for item in items.values():
                if fnmatch.fnmatch(query, item.name):
                    result['items'][item.name] = item
                    tmp = item.location.split(':', 1)
                    if not item.name in result['locations']:
                        result['locations'][item.name] = []
                        result['values'][item.name] = []
                    if item['own_value']!=None:
                        result['values'][item.name] = item['own_value']
                    result['locations'][item.name].append((tmp[1], item['type']))
        result['items'] = sorted(list(result['items'].values()), key=lambda item: item.name)
        return result

def format_value(value):
    value = DatabaseOutputHelpers.split_hex(DatabaseOutputHelpers.encode_binary(value))
    # value = value.replace('\\', '\\\\').replace('"', '\\"')
    return value

def print_formatted(format, query, name):
    suffix = ''
    if format=='auto_init':

        macro = 'AUTO_STRING_DEF'
    elif format=='declare':
        macro = 'PROGMEM_STRING_DECL'
        print('%s(%s)' % (macro, name))
        return
    else:
        suffix = ';'
        macro = 'PROGMEM_STRING_DEF'

    l = []
    for loc in query['locations'][item.name]:
        l.append('%s:%s' % (loc[1], loc[0]))
    l = sorted(list(set(l)))


    print('// %s' % ', '.join(l))
    print('%s(%s, "%s")%s' % (macro, name, format_value(query['values'][name]), suffix))

    # query['locations'][name]


parser = argparse.ArgumentParser(description='QueryDB')
parser.add_argument('-d', '--database-dir', help="database directory", required=True)
parser.add_argument('-q', '--query', help="query database. wildcards allowed")
parser.add_argument('-f', '--format', help='query output format', choices=['auto_init', 'define', 'declare'])
# parser.add_argument('--cache', help="temporary file to cache the preprocessor object", type=argparse.FileType('r+b'))
# parser.add_argument('-v', '--verbose', help='enable verbose output', action='store_true', default=False)
args = parser.parse_args()

debug_db_file = path.join(args.database_dir, '_debug.json')
db_file = path.join(args.database_dir, 'database.pickle')
if not path.isfile(db_file):
    db_file += '.xz'
    if not path.isfile(db_file):
        args.error('cannot find database in %s' % args.database_dir)

with FileWrapper.open(db_file, 'rb') as file:
    data = pickle.load(file)
    db = Database(data)

if not args.query:
    print('Database info')
    print('-'*40)
    print('items %u' % db.item_count)
    print('values %u' % db.values_count)
    print('source locations %u' % db.source_locations)
    print('static items %u' % db.static_count)
    sys.exit(0)

query = db.query(args.query)
if not query['items']:
    print('could not find any item for "%s"' % args.query);
    sys.exit(0)
if args.format:
    for item in query['items']:
        print_formatted(args.format, query, item.name)
else:
    query['items'] = [item.name for item in query['items']]
    pprint(query)