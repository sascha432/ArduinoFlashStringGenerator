#
# Author: sascha_lammers@gmx.de
#

import argparse
import sys
import pickle
import fnmatch
from os import path
import re
from pprint import pprint
from generator import FileWrapper, DefinitionType, DatabaseHelpers

class Database(object):
    def __init__(self, data):
        self.source_locations = 0
        self.static_count = 0
        self._unique = {}
        self._unique_name = {}
        self._targets = data['targets']
        self._defined = data['defined']
        self._items = data['items']
        self._values = {}
        self._source_files = []
        self._static = []
        for target_idx, items in self._items.items():
            self.source_locations += len(items)
            for item in items.values():
                tmp = item.location.split(':', 2)
                if not tmp[1] in self._source_files:
                    self._source_files.append(tmp[1])
                if not item.name in self._values:
                    self._values[item.name] = None
                if item['own_value']!=None:
                    if self._values[item.name]!=self._values[item.name]:
                        raise RuntimeError('value for %s changed' % item.name)
                    self._values[item.name] = item['own_value']
                if item['type']==DefinitionType.DEFINE:
                    self.static_count += 1
                    self._static.append(item.name)
                if not item.name in self._unique:
                    self._unique[item.name] = {}
                if item.index in self._unique[item.name] and item['type']!=DefinitionType.AUTO_INIT:
                    # print(item)
                    # print(self._unique[item.name][item.index])
                    print('WARNING! index=%s duplicate target=%s' % (item.index, target_idx))
                    # raise RuntimeError('index %s duplicate' % item.index)
                self._unique[item.name][item.index] = item
        self._static = list(set(self._static))

    @property
    def item_count(self):
        return len(self._unique)

    @property
    def values_count(self):
        return sum([(val!=None and 1 or 0) for val in self._values.values()])

    @property
    def source_files_count(self):
        return sum([1 for val in self._source_files if re.match(r'.*\.(c|C|cc|cpp|ino|INO)\Z', val)])

    def get_value(self, name):
        if name in self._values:
            return self._values[name]
        return DatabaseHelpers.beautify(name)

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
                if fnmatch.fnmatch(item.name, query):
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
    value = DatabaseHelpers.split_hex(DatabaseHelpers.encode_binary(value))
    # value = value.replace('\\', '\\\\').replace('"', '\\"')
    return value

def print_formatted(format, query, item):
    if format=='kv':
        print('%s=%s' % (item.name, query['values'][item.name]))
        return
    elif format=='declare':
        macro = 'PROGMEM_STRING_DECL'
        print('%s(%s)' % (macro, item.name))
        return
    elif format=='auto_init':
        suffix = ''
        macro = 'AUTO_STRING_DEF'
    else:
        suffix = ';'
        macro = 'PROGMEM_STRING_DEF'

    l = []
    for loc in query['locations'][item.name]:
        l.append('%s:%s' % (loc[1], loc[0]))
    l = sorted(list(set(l)))


    print('// %s' % ', '.join(l))
    print('%s(%s, "%s")%s' % (macro, item.name, format_value(query['values'][item.name]), suffix))

    # query['locations'][name]


parser = argparse.ArgumentParser(description='QueryDB')
parser.add_argument('-d', '--database-dir', help='database directory', required=True)
parser.add_argument('-q', '--query', help='query database. wildcards allowed')
parser.add_argument('-f', '--format', help='query output format', choices=['auto_init', 'define', 'declare', 'kv'])
parser.add_argument('-l', '--list', help='list source files', action='store_true')
parser.add_argument('-c', '--create', help='create spgm_auto_strings.*', nargs=2)
# parser.add_argument('--cache', help='temporary file to cache the preprocessor object', type=argparse.FileType('r+b'))
# parser.add_argument('-v', '--verbose', help='enable verbose output', action='store_true', default=False)
args = parser.parse_args()

debug_db_file = path.join(args.database_dir, '_debug.json')
db_file = path.join(args.database_dir, 'database.pickle')
if not path.isfile(db_file):
    db_file += '.xz'
    if not path.isfile(db_file):
        parser.error('cannot find database in %s' % args.database_dir)

with FileWrapper.open(db_file, 'rb') as file:
    data = pickle.load(file)
    db = Database(data)

def check_auto_gen_file(filename):
    if not path.isfile(filename):
        return
    with open(filename, 'rt') as file:
        if 'AUTO GENERATED FILE - DO NOT MODIFY' in file.readline():
            return

    parser.error('output file %s exists and does not seem to be auto generated' % filename)


if args.create:

    header = path.abspath(args.create[0])
    source = path.abspath(args.create[1])

    check_auto_gen_file(header)
    check_auto_gen_file(source)

    with open(header, 'wt') as file:
        print('// AUTO GENERATED FILE - DO NOT MODIFY', file=file)
        print('#pragma once', file=file)
        print('#include <Arduino_compat.h>', file=file)
        print('#ifdef __cplusplus', file=file)
        print('extern "C" {', file=file)
        print('#endif', file=file)

        for item in db._unique.values():
            item = list(item.values())[0]
            print('PROGMEM_STRING_DECL(%s);' % item.name, file=file)

        print('#ifdef __cplusplus', file=file)
        print('} // extern "C"', file=file)
        print('#endif', file=file)

        print('created %s' % header)

    with open(source, 'wt') as file:
        print('// AUTO GENERATED FILE - DO NOT MODIFY', file=file)
        print('#include "spgm_auto_strings.h"', file=file)

        for item in db._unique.values():
            item = list(item.values())[0]
            if not item.name in db._static:
                # if item['value']:
                try:
                    print('PROGMEM_STRING_DEF(%s, "%s");' % (item.name, DatabaseHelpers.split_hex(DatabaseHelpers.encode_binary(db.get_value(item.name)))), file=file)
                except:
                    pass

        print('created %s' % source)

    sys.exit(0)

if args.list:
    for file in sorted(db._source_files):
        print(file)
    sys.exit(0)

if not args.query:
    print('Database info')
    print('-'*40)
    print('items %u' % db.item_count)
    print('values %u' % db.values_count)
    print('source locations %u' % db.source_locations)
    print('source files %u' % db.source_files_count)
    print('static items %u' % db.static_count)
    sys.exit(0)

query = db.query(args.query)
if not query['items']:
    print('could not find any item for "%s"' % args.query);
    sys.exit(0)
if args.format:
    for item in query['items']:
        print_formatted(args.format, query, item)
else:
    query['items'] = [item.name for item in query['items']]
    pprint(query)