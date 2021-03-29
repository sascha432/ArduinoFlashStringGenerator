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

    database = None # type: Database

    def getDatabaseInstance():
        return v2.database

    class Value(object):
        def __init__(self, value, auto=False, override=False):
            self._value = value
            self._auto = auto
            self._override = override

        def can_override(self, obj):
            if obj._value==None or self._override==False:
                return False
            if self._auto==True and obj._auto==False:
                return True
            if self._value==None:
                return True
            if self._value==obj._value and id(self)!=id(obj):
                return True
            return False

        def __eq__(self, obj):
            return id(self)==id(obj)

    class Item(dict):
        def __init__(self, *args, **kwargs):
            if len(args)==1:
                self.__init_item__(*args)
            elif len(args)==5:
                self.__init_args__(*args)
            else:
                raise RuntimeError('invalid args=%u' % len(args))

        def __init_args__(self, name, type, source, value=None, auto=None):
            self._database = v2.getDatabaseInstance()
            if not isinstance(type, DefinitionType):
                raise RuntimeError('invalid type=%s' % type(type))
            dict.__init__(self, {
                'name': name,
                'type': type,
                'source': source,
                'value': value,
                'auto': auto,
                'vdb': False,
                'adb': False
            });

        def __init_item__(self, item):
            self.__init__(item['name'], item['type'], item['source'], item['value'], item['auto']);

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
        def locations(self):
            return self._database.get_locations(self)

        @property
        def location(self):
            return '%s:%s' % (self.__getitem__('type'), self.__getitem__('source'))

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
            return (self.__class__, (self['name'], self['type'], self['source'], self['value'], self['auto']))


class Database(object):
    def __init__(self, generator, target):

        # Database is a singleton
        if v2.database:
            raise RuntimeError('Database already created')
        v2.database = self

        self._generator = generator

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

        # hash target and sources to identify in database
        self._target = target;
        self._sources_hash = None
        # self._target_hash = None
        if target!=None:
            targets = []
            sources = []
            for node in self._target:
                targets.append(node.get_path())
                sources.append(node.srcnode().get_path())
            self._sources_hash = hash(','.join(sources))
            self._target_hash = hash(','.join(targets))

    @property
    def config(self):
        return self._generator.config

    @property
    def source_idx(self):
        return self._sources_hash

    def get_target(self):
        if not self._target_hash in self._targets:
            self._targets[self._target_hash] = {
                'files': [],
                'files_hash': None
            }
        return self._targets[self._target_hash]

    # create a sorted list of all stored locations
    def get_locations(self, find_item):
        locations = []
        if find_item.index in self._defined:
            locations.append(self._defined[find_item.index].location)
        for item in self._defined.values():
            if find_item.name==item.name:
                locations.append(item.location)
        for items in self._items_per_file.values():
            if find_item.index in items:
                locations.append(items[find_item.index].location)
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
                raise RuntimeError('cannot redefine %s %s!=%s' % (name, value, self._values[name]))
        if value==None:
            return False
        self._values[name] = value
        return True

    # create a human readable version
    def write_json(self):

        # start = time.monotonic()

        os.makedirs(self._dir, exist_ok=True)

        tmp = {
            'defined': {},
            'unique': {}
        }
        for source_idx, items in self._items_per_file.items():
            tmp[source_idx] = {}
            for index, item in items.items():
                item_out = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'auto': item['auto']}
                if not item.name in tmp['unique']:
                    tmp['unique'][item.name] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'auto': item['auto'], 'locations': str(item.locations)}
                tmp[source_idx][index] = item_out
        if self._defined:
            for index, item in self._defined.items():
                tmp['defined'][index] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'auto': item['auto']}
                if not item.name in tmp['unique']:
                    tmp['unique'][item.name] = {'name': item['name'], 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'auto': item['auto'], 'locations': str(item.locations)}

        with open(self._json_file, 'wt') as file:
            file.write(json.dumps(tmp, indent=2))

        # dur = time.monotonic() - start
        # print('DEBUG written to %s: time %.3fms' % (self._json_file, dur * 1000))

    # read shard or raw file with return_result=True
    def read_shard(self, filename, return_result=False):
        if not path.isfile(filename) and return_result:
            return {}

        file = FileWrapper.open(filename, 'rb')
        try:
            items = pickle.load(file)
            if return_result:
                return items
        finally:
            file.close()
        for source_idx, items in items.items():
            self._items_per_file[source_idx] = items
            for item in items.values():
                item['vdb'] = True
                item['adb'] = True
                self.merge(item)

    def merge_defined(self, defined):
        # print("MERGE %u" % len(defined))
        if defined:
            old = len(self._defined)
            self._defined.update(defined)
            for item in self._defined.values():
                self.merge(item)
            if old!=len(self._defined):
                print("DEBUG: defined changed from %u to %u" % (old, len(self._defined)))


    # read database
    def read(self):

        start = time.monotonic()

        if not self._lock.acquire(True, 60.0):
            raise RuntimeError('Failed to acquire database lock')
        try:

            self._defined = {}
            self._items_per_file = {}
            if self._target==None:
                return

            dir = path.join(self._dir, '*.pickle*')
            files = glob.glob(dir);
            if not files:
                return

            defined = None
            shards = len(files)
            for file in files:
                if 'defines.pickle' in file:
                    defined = self.read_shard(file, True)
                else:
                    self.read_shard(file)

            self.merge_defined(defined)

            # print('DEBUG read from %s: %u entries %u locations %u shards' % tuple([dir] + list(self.llen(self._items)) + [shards]))
        finally:
            self._lock.release();

        self.dump();

    # write single shard or entire database to file
    def write_shard(self, path, source_idx=None, defines=False):

        if defines==False and source_idx!=None and (not source_idx in self._items_per_file or not self._items_per_file[source_idx]):
            return None

        compressed_file = path + '.xz'
        if self.config.build_database_compression == CompressionType.LZMA:
            filename = compressed_file
        else:
            filename = path

        # get a fresh copy from disk while the database is locked
        items = self.read_shard(filename, True)
        if defines:
            self.merge_defined(items)
            items = self._defined
        else:
            # replace the current target
            items[source_idx] = self._items_per_file[source_idx]

        file = FileWrapper.open(filename, 'wb')
        try:
            pickle.dump(items, file)
        finally:
            file.close()

        if defines:
            return [filename] + list(self.llen(self._defined))

        return [filename] + list(self.llen(items[source_idx]))

    # write database
    def write(self):
        if self._target==None:
            return

        start = time.monotonic()

        if not self._lock.acquire(True, 60.0):
            time.sleep(5)
            if not self._lock.acquire(True, 60.0):
                raise RuntimeError('Failed to acquire database lock')
        try:

            os.makedirs(self._dir, exist_ok=True)

            num_shards = self.config.build_database_num_shards
            if num_shards>1:
                shard = self.source_idx % num_shards
                file = path.join(self._dir, '%04x%04x.pickle' % (num_shards, shard))
                result = self.write_shard(file, self.source_idx)
            else:
                file = path.join(self._dir, 'spgm.pickle')
                shard = 0
                result = self.write_shard(file)


            file = path.join(self._dir, 'defines.pickle')
            self.write_shard(file, None, True)

            self.write_json()

            if result:
                dur = time.monotonic() - start
                print('DEBUG written to %s: entries=%u locations=%u shard=%u/%u time=%.3fms' % (*result, shard + 1, num_shards, dur * 1000))

        finally:
            self._lock.release()

        self.dump();

    # dump database
    def dump(self):
        return;
        print("---------------------------------------------")
        for source_idx, items in self._items_per_file.items():
            for index, item in items.items():
                print(source_idx, index, item['type'], item['name'], item['locations'])
        print("---------------------------------------------")

    # merge item from current target into all items
    def merge(self, item):
        if 'name' not in item:
            print('item %s' % item)
            raise RuntimeError('invalid item')
        if not isinstance(item, v2.Item):
            raise RuntimeError('type %s not %s', type(item), type(v2.Item))

        if item['type'] in (DefinitionType.DEFINE, DefinitionType.AUTO_INIT):
            value = item['value']
            if value==None and item['auto']!=None:
                value=item['auto']
            if value==None:
                item['auto'] = Database.beautify(item.name)
                item['value'] = item['auto']
                value = item['auto']
            self._defined[item.index] = v2.Item(item);
        # if item.index in self._items:
        #     item2 = self._items[item.index]
        #     if item2['value']!=None and item['value']==None:
        #         item['value'] = item2['value']
        #     elif item['value']!=None and item2['value']==None:
        #         item2['value'] = item['value']
        #     else:
        #         if item['value']!=item2['value']:
        #             print('%s!=%s' % (item['value'], item2['value']))
            # else:
            #     item2.update({
            #         'value': item['value'],
            #         'auto': item['auto']
            #     })
        #     return
        # self._items[item.index] = item

    def llen(self, items):
        entries = 0
        locations = 0
        try:
            for item in items.values():
                entries += 1
                locations += len(item['locations'])
        except:
            entries = len(items)
            locations = 0
        return (entries, locations)

    # returns True for items that are statically defined
    def is_static(self, item):
        if item['type']==DefinitionType.DEFINE:
            return True
        for loc in item.locations:
            if loc.startswith('PROGMEM_STRING_DEF:'):
                return True
        return False

    # def rebuild_items(self):
    #     if self._target==None:
    #         return
    #     old = self.llen(self._items)
    #     self._items = {}
    #     for items in self._items_per_file.values():
    #         for item in items.values():
    #             self.merge(item)
    #     for item in self._defined.values():
    #         self.merge(item)
    #     new = self.llen(self._items)
    #     print('DEBUG rebuild items (old %u, %u -> new %u, %u)' % tuple(list(old) + list(new)))

    # remove the values from the current target
    def flush(self):
        if self._target==None:
            return
        if self.source_idx in self._items_per_file:
            print('DEBUG removing %u entries in %u locations' % self.llen(self._items_per_file[self.source_idx]));
            self._items_per_file[self.source_idx] = {}

    # add or update an item
    def add(self, source, name, type, value, auto_value):
        # print('%s: source=%s name=%s type=%s value=%s auto=%s' % (self.source_idx, source, name, type, value, auto_value))
        if not self.source_idx in self._items_per_file:
            self._items_per_file[self.source_idx] = {}
        items = self._items_per_file[self.source_idx]

        if name in items:
            item = items[name]
            # if item['type']!=type:
            #     raise RuntimeError('invalid type %s!=%s' % (type, item['type']))
            if item.name!=name:
                raise RuntimeError('invalid name %s!=%s' % (name, item.name))
            if item['value']==None:
                if value!=None:
                    item['value'] = value
                    item['vdb'] = False
            elif value!=None and item['value']!=value:
                if item['vdb']==False:
                    raise RuntimeError('invalid value %s!=%s' % (value, item['value']))
                else:
                    print("value of %s was modified" % (name))
                    item['value'] = value
                    item['vdb'] = False
            if item['auto']==None:
                if auto_value!=None:
                    item['auto'] = auto_value
                    item['adb'] = False
            elif auto_value!=None and item['auto']!=auto_value:
                if item['adb']==False:
                    raise RuntimeError('invalid value %s!=%s' % (auto_value, item['auto']))
                else:
                    print("auto value of %s was modified" % (name))
                    item['auto'] = auto_value
                    item['adb'] = False
            self.merge(item)
        else:
            items[name] = v2.Item(name, type, source, value, auto_value);
            self.merge(items[name])

    def item_location(self, item):
        return '%s:%s' % (item['type'], item['source'])

    # add items from preprocessor
    def add_items(self, items):
        if self._target==None:
            return
        for item in items:
            self.add(item['source'], item['name'], DefinitionType.fromString(item['type']), item['value'], item['auto'])

        self.write();

    # write locations
    def write_locations(self, file: TextIOWrapper, item):
        if self.config.locations_one_per_line:
            file.write('//' + '\n//'.join(item.locations))
        else:
            file.write('// %s\n' % ', '.join(item.locations))

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

    # write defintion string
    def write_define(self, file: TextIOWrapper, item):
        lang = 'default'
        if item['value']!=None:
            value = item['value']
        elif item['auto']!=None:
            value = item['auto']
            lang += ' (auto)'
        else:
            value = Database.beautify(item['name'])
            lang += ' (auto)'

        self.write_locations(file, item)
        file.write('PROGMEM_STRING_DEF(%s, "%s"); // %s\n' % (item.name, Database.split_hex(value), lang))

