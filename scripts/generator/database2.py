#
# Author: sascha_lammers@gmx.de
#

import threading
import sys
import pickle
import time
import glob
import os
import re
import json
from os import path
from .types import CompressionType, DefinitionType
from .file_wrapper import FileWrapper
from io import TextIOWrapper

class v2:

    class Value(object):
        def __init__(self, value, override=False):
            self._value = value
            self._override = override

        def can_override(self, obj):
            if obj._value==None or self._override==False:
                return False
            if self._value==None:
                return True
            if self._value==obj._value and id(self)!=id(obj):
                return True
            return False

        def __eq__(self, obj):
            return id(self)==id(obj)

    class Item(dict):
        def __init__(self, name, type, source, value=None, data={}):
            if not isinstance(type, DefinitionType):
                type = DefinitionType.fromString(type)
            dict.__init__(self, {
                'name': name,
                'type': type,
                'source': source,
                'value': value,
                'data': data
            });

        # def __init_item__(self, item):
        #     self.__init__(item['name'], item['type'], item['source'], item['value'], item['data']);

        @property
        def name(self):
            return dict.__getitem__(self, 'name')

        @property
        def index(self):
            # unique key on c source file, line and name
            # in theory there could be multiple per line but the column is not stored
            id_str = ':'.join([self.__getitem__('source'), str(self.__getitem__('type')), self.name])
            return hash(id_str)

        @property
        def value(self):
            value = self.__getitem__('value')
            if value==None:
                value = DatabaseOutputHelpers.beautify(self.name)
            return value

        @property
        def locations(self):
            return self._database.get_locations(self)

        @property
        def location(self):
            return '%s:%s' % (self.__getitem__('type'), self.__getitem__('source'))

        @property
        def has_value(self):
            return self.__getitem__('value')!=None

        def __getitem__(self, key):
            if key=='locations':
                return self.locations
            if key=='value':
                val = self._database.get_value(self, self.name)
                if val!=None:
                    return val
            return super().__getitem__(key)

        def __setitem__(self, key, val):
            if key=='locations':
                return None
            if key=='value':
                if not self._database.set_value(self, self.name, val):
                    return
            return super().__setitem__(key, val)

        def __reduce__(self):
            return (self.__class__, (self['name'], self['type'], self['source'], self['value'], self['data']))



class DatabaseOutputHelpers(object):

    # write locations
    def write_locations(self, file: TextIOWrapper, item, indent=''):
        if self.config.locations_one_per_line:
            file.write('%s//' + ('\n%s//' % indent).join(indent, item.locations))
        else:
            file.write('%s// %s\n' % (indent, ', '.join(item.locations)))

    def beautify(name):
        name = name.replace('_', ' ')
        return name

    # split hex values and trailing hexdigits into separate strings
    # "\xc2\xb0C\xc2\xb0F\xc2\xb0K" = "\xc2\xb0" "C\xc2\xb0" "F\xc2\xb0K"
    def split_hex(value):
        if value.find('\\x')==-1:
            return value
        def repl(m):
            return '%s\" \"%s' % (m.group(1), m.group(2))
        new_value = re.sub('(\\\\x[0-9a-fA-F]{2})([0-9a-fA-F])', repl, value);
        # if new_value != value:
        #     print('"%s" "%s"' % (new_value, value))
        return new_value

    # get unique items that are not static
    def get_items(self, static=False):
        items_out = {}
        for items in self._items_per_file.values():
            for item in items.values():
                if item.name not in items_out and self.is_static(item)==static:
                    items_out[item.name] = item
        for item in self._defined.values():
            if item.name not in items_out and self.is_static(item)==static:
                items_out[item.name] = item
        return items_out

    # get unique items that are static
    def get_static_items(self):
        return self.get_items(True)

    # encode binary data into hexadecimal string
    def encode_binary(s: str):
        bytes = s.encode('ascii', errors='backslashreplace')
        out = ''
        for byte in bytes:
            if byte&0x80:
                out += '\\x%02x' % byte
            else:
                out += chr(byte)
        return out

    def create_define(self, item):
        try:
            ascii_str = DatabaseOutputHelpers.encode_binary(item.value)
        except UnicodeEncodeError as e:
            self.add_error('failed to encode string', item=item, fatal=True)

        s = '(%s, "%s");' % (item.name, DatabaseOutputHelpers.split_hex(ascii_str))
        return s

    # write definition string
    def write_define(self, file: TextIOWrapper, item: v2.Item):
        lang = 'default'
        if not item.has_value:
            lang += ' (auto)'
        self.write_locations(file, item)
        print('%-160.65535s // %s' % ('PROGMEM_STRING_DEF' + self.create_define(item), lang), file=file)

    # write auto definition
    def write_auto_init(self, file: TextIOWrapper, item: v2.Item):
        if item['value']!=None:
            raise RuntimeError('value expected to be None')
        indent = 4*' '
        self.write_locations(file, item, indent)
        print('%sAUTO_STRING_DEF%s' % (indent, self.create_define(item)), file=file)


class Database(DatabaseOutputHelpers):
    def __init__(self, generator, target):

        self._generator = generator

        # list of errors during generating
        self._errors = []

        # output directory
        self._dir = path.abspath(self.config.build_database_dir);

        # human readable version of the database fopr debugging
        self._json_file = path.join(self._dir, '_debug.json');

        # lock for the database files
        self._lock = threading.Lock()

        # all values by name
        self._values = {}
        # all items with a defined value
        self._defined = {}
        # all items that belong to a target, usually a C file
        self._items_per_file = {}
        # list of targets and dependecies
        self._targets = {}

        def make_unsigned_hex64(val):
            if val<0:
                val = (1 << 63) + val
                return 'f' + ('%016x' % val)[1:]
            return '%016x' % val


        # hash target and sources to identify in database
        self._target = target;
        targets = []
        for node in self._target:
            targets.append(node.get_path())
        self._targets_hash = hash(','.join(targets))
        self._target_idx = make_unsigned_hex64(self._targets_hash)

        # self._sources_hash = None
        # self._target_hash = None
        # if target!=None:
        #     targets = []
        #     sources = []
        #     for node in self._target:
        #         targets.append(node.get_path())
        #         sources.append(node.srcnode().get_path())
        #     self._sources_hash = hash(','.join(sources))
        #     self._target_idx = make_unsigned_hex64(self._source_hash)
        #     self._targets_hash = make_unsigned_hex64(hash(','.join(targets)))

    @property
    def config(self):
        return self._generator.config

    def get_target(self):
        if not self._target_idx in self._targets:
            self._targets[self._target_idx] = {
                'files': [],
                'hash': None
            }
        return self._targets[self._target_idx]

    def add_target_files(self, files, hash):
        self._targets[self._target_idx] = {
            'files': files,
            'hash': hash
        }

    # create a sorted list of all stored locations
    def get_locations(self, find_item):
        locations = []
        if find_item.name in self._defined:
            locations.append(self._defined[find_item.name].location)

        # for item in self._defined.values():
        #     if find_item.name==item.name:
        #         locations.append(item.location)

        for items in self._items_per_file.values():
            # if find_item.index in items:
            #     locations.append(items[find_item.index].location)
            for item in items.values():
                if find_item.name==item.name:
                    locations.append(item.location)
        locations = sorted(list(set(locations)), key=lambda val: val)
        return locations

    def get_value(self, item, name):
        if name in self._values:
            return self._values[name]
        return None

    def set_value(self, item, name, value):
        if name in self._values:
            if value!=self._values[name]:
                self.add_error('cannot redefine different value: %s!=%s' % (name, value, self._values[name]), item=item)
        if value==None:
            return False
        self._values[name] = value
        return True

    def add_error(self, msg, item=None, item2=None, fatal=False):
        if item:
            msg += '\nitem name: %s source: %s' % (item.name, item['source'])
            if item.has_value:
                msg += ' value: "%s"' % item['value']
        if item2:
            msg += '\nitem name: %s source: %s' % (item2.name, item2['source'])
        self._errors.append(msg)
        if fatal:
            self.print_errors()
            self._generator._env.Exit(1)

    def print_errors(self):
        for error in self._errors:
            print(error, file=sys.stderr)
            print('', file=sys.stderr)

    def _add_extension(self, file):
        if self.config.build_database_compression == CompressionType.LZMA:
            file += '.xz'
        return file

    # create a human readable version of the database for debugging
    def write_json(self):

        os.makedirs(self._dir, exist_ok=True)

        tmp = {
            'defined': {},
            'unique': {},
            'targets': self._targets
        }
        for target_idx, items in self._items_per_file.items():
            tmp[target_idx] = {}
            for index, item in items.items():
                item_out = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value']}
                if not item.name in tmp['unique']:
                    tmp['unique'][item.name] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'locations': str(item.locations)}
                tmp[target_idx][index] = item_out
        if self._defined:
            for index, item in self._defined.items():
                tmp['defined'][index] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value']}
                if not item.name in tmp['unique']:
                    tmp['unique'][item.name] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'locations': str(item.locations)}

        with open(self._json_file, 'wt') as file:
            file.write(json.dumps(tmp, indent=2))

    # assign self to _database of each item
    def _update_items(self, items: dict):
        for item in items.values():
            item._database = self

    # load database from file if it is exists
    def _read(self, filename):
        if not path.isfile(filename):
            return {'defined': {}, 'targets': {}, 'items': {}}

        file = FileWrapper.open(filename, 'rb')
        try:
            database = pickle.load(file)
        finally:
            file.close()

        return database

    # write database to file
    def _write(self, filename, database: dict):

        file = FileWrapper.open(filename, 'wb')
        try:
            pickle.dump(database, file)
        finally:
            file.close()

    # read database
    def read(self):

        if not self._lock.acquire(True, 60.0):
            self.add_error('failed to acquire database read lock', fatal=True)
        try:

            file = self._add_extension(path.join(self._dir, 'database.pickle'))
            database = self._read(file)
            self._targets = database['targets']
            self._defined = database['defined']
            self._items_per_file = database['items']

            self._update_items(self._defined)
            for items in self._items_per_file.values():
                self._update_items(items)
        finally:
            self._lock.release();

    # write database
    def write(self):

        if not self._lock.acquire(True, 60.0):
            self.add_error('failed to acquire database write lock', fatal=True)
        try:

            os.makedirs(self._dir, exist_ok=True)
            file = self._add_extension(path.join(self._dir, 'database.pickle'))

            merged_database = self._read(file)
            merged_database['targets'].update(self._targets)
            merged_database['defined'].update(self._defined)
            if self._target_idx in self._items_per_file:
                merged_database['items'].update({self._target_idx: self._items_per_file[self._target_idx]})
            self._update_items(merged_database['defined'])
            for items in merged_database['items'].values():
                self._update_items(items)
            self._write(file, merged_database)

            self.write_json()

        finally:
            self._lock.release()

    # returns True for items that are statically defined
    def is_static(self, find_item):
        if find_item['type']==DefinitionType.DEFINE:
            return True

        for items in self._items_per_file.values():
            for item in items.values():
                if item['type']==DefinitionType.DEFINE and find_item['name']==item['name']:
                    if self.is_static_old(item)!=True:#DEBUG
                        raise RuntimeError('is_static error')#DEBUG
                    return True

        if self.is_static_old(find_item)!=False:#DEBUG
            raise RuntimeError('is_static error')#DEBUG
        return False

    def is_static_old(self, item):#DEBUG REMOVE
        if item['type']==DefinitionType.DEFINE:
            return True
        for loc in item.locations:
            if loc.startswith('PROGMEM_STRING_DEF:'):
                return True
        return False

    # returns True if the item is currently in use
    def is_used(self, find_item):
        for items in self._items_per_file.values():
            for item in items.values():
                if item['type']==DefinitionType.SPGM and item.name==find_item.name:
                    return True
        return False

    # remove the values from the current target
    def flush(self):
        if self._target_idx in self._items_per_file:
            self._items_per_file[self._target_idx] = {}

    # add or update an item
    def add(self, source, name, type, value, data):
        # print('%s: source=%s name=%s type=%s value=%s' % (self._target_idx, source, name, type, value))

        # create dict for this target if it does not exist
        if not self._target_idx in self._items_per_file:
            self._items_per_file[self._target_idx] = {}
        items = self._items_per_file[self._target_idx]

        # check if item already exists
        new_item = v2.Item(name, type, source, value, data);
        new_item._database = self
        if new_item.index in items:
            self.add_error('item already exists. currently only one item per line may exist', item=new_item, fatal=True) #TODO fix issue

        # add item
        items[new_item.index] = new_item

        # add item to defined items if it has a value
        if new_item['value']!=None:
            if new_item.name in self._defined:
                if self._defined[new_item.name]['value']!=new_item['value']:
                    self.add_error('cannot redefine different value: %s!=%s' % (new_item['value'], self._defined[new_item.name]['value']), item=new_item, item2=self._defined[new_item.name])
            else:
                self._defined[new_item.name] = new_item

    # add items from preprocessor
    def add_items(self, items):
        for item in items:
            self.add(item['source'], item['name'], item['type'], item['value'], item['data'])

        # rewrite database
        self.write();

