#
# Author: sascha_lammers@gmx.de
#

try:
    from ..spgm_extra_script import SpgmExtraScript
except:
    pass
from io import TextIOWrapper
import pickle
from SCons.Node import FS
import sys
import os
import json
import threading
import time
import glob
import re
import pickle
from os import path
from .types import CompressionType, ItemType, DebugType, DefinitionType
from .item import Item
from .config import SpgmConfig
import generator
from .build_database import BuildDatabase
from typing import List, Dict, Iterable, Any

setattr(generator, 'get_spgm_extra_script', lambda: generator.spgm_extra_script)

# detect compression format by file extension
class FileWrapper(object):
    def __init__(self, file, filename, mode, is_open=True):
        self._file = file
        self._filename = filename
        self._mode = mode
        self._is_open = is_open

    def open(filename, mode):
        if filename.lower().endswith('.xz'):
            module = 'lzma'
        else:
            module = 'builtins'
        module = __import__(module)
        return FileWrapper(getattr(module, 'open')(filename, mode), filename, mode, True)

    @property
    def name(self):
        return object.__getattribute__(self, 'name')

    @property
    def mode(self):
        return object.__getattribute__(self, 'mode')

    @property
    def closed(self):
        return object.__getattribute__(self, 'closed')

    def close(self):
        file = object.__getattribute__(self, '_file')
        self._is_open = False
        file.close()

    def __getattribute__(name):
        return object.__getattribute__(FileWrapper, name)

    def __getattribute__(self, name):
        if name=='close':
            return object.__getattribute__(self, 'close')
        file = object.__getattribute__(self, '_file')
        if hasattr(file, name):
            return getattr(file, name)
        if name=='name':
            return object.__getattribute__(self, '_filename')
        if name=='mode':
            return object.__getattribute__(self, '_mode')
        if name=='closed':
            return not object.__getattribute__(self, '_is_open')
        # raise exception
        return object.__getattribute__(file, name)

class FileLocation(object):
    def __init__(self, source, line, type):
        self.source = source
        self.line = line
        self.type = type

class ValueObject(object):
    def __init__(self, value=None):
        self._value = value

    @property
    def has_value(self):
        return self._value!=None

    @property
    def value(self):
        return self._value;

class Database(object):
    def __init__(self, generator, target):
        self._generator = generator
        self._dir = path.abspath(self.config.build_database_dir);
        self._json_file = path.join(self._dir, '_debug.json');
        self._lock = threading.Lock()
        self._defined = {}
        self._items = {}
        self._items_per_file = {}
        self._target = target;
        self._sources = None
        self._sources_hash = None
        if target!=None:
            sources = []
            for n in self._target:
                sources.append(n.srcnode().get_path())
                # sources.append(n.srcnode().get_abspath())
            self._sources = ','.join(sources)
            self._sources_hash = hash(self._sources)

    @property
    def config(self):
        return self._generator.config

    @property
    def source_idx(self):
        return self._sources_hash

    # create a human readable version
    def write_json(self):

        start = time.monotonic()

        os.makedirs(self._dir, exist_ok=True)

        tmp = {}
        for sources, items in self._items_per_file.items():
            tmp[sources] = {}
            for name, item in items.items():
                item2 = {}
                for key, val in item.items():
                    if val==None:
                        pass
                    elif type(val) in(str, int, float, None):
                        item2[key] = val
                    else:
                        item2[key] = str(val)
                del item2['vdb']
                del item2['adb']
                loc = '%s:%s' % (item['type'], item['source'])
                # if loc in item['locations']:
                #     del item2['source']
                #     del item2['type']
                tmp[sources][name] = item2
        tmp['defined'] = {}
        if self._defined:
            for name, item in self._defined.items():
                tmp['defined'][name] = {'name': name, 'source': item['source'], 'type': str(item['type']), 'value': item['value'], 'auto': item['auto']}

        with open(self._json_file, 'wt') as file:
            file.write(json.dumps(tmp, indent=2))

        dur = time.monotonic() - start
        print('DEBUG written to %s: time %.3fms' % (self._json_file, dur * 1000))

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
        print("MERGE %u" % len(defined))
        if defined:
            old = len(self._defined)
            self._defined.update(defined)
            for item in self._defined.values():
                self.merge(item)
            print("DEBUG: defined changed from %u to %u" % (old, len(self._defined)))


    # read database
    def read(self):

        start = time.monotonic()

        if not self._lock.acquire(True, 60.0):
            time.sleep(5)
            if not self._lock.acquire(True, 60.0):
                raise RuntimeError('Failed to acquire database lock')
        try:

            self._defined = {}
            self._items = {}
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

            print('DEBUG read from %s: %u entries %u locations %u shards' % tuple([dir] + list(self.llen(self._items)) + [shards]))
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

            if result:
                dur = time.monotonic() - start
                print('DEBUG written to %s: entries=%u locations=%u shard=%u/%u time=%.3fms' % (*result, shard + 1, num_shards, dur * 1000))

            self.write_json()

        finally:
            self._lock.release()

        self.dump();

    # dump database
    def dump(self):
        return;
        print("---------------------------------------------")
        for name, item in self._items.items():
            print(name, item['type'], item['name'], item['locations'])
        print("---------------------------------------------")
        for source_idx, items in self._items_per_file.items():
            for name, item in items.items():
                print(source_idx, name, item['type'], item['name'], item['locations'])
        print("---------------------------------------------")

    # merge item from current target into all items
    def merge(self, item):
        if 'name' not in item:
            print('item %s' % item)
            raise RuntimeError('invalid item')

        if item['type'] in (DefinitionType.DEFINE, DefinitionType.AUTO_INIT):
            value = item['value']
            if value==None and item['auto']!=None:
                value=item['auto']
            if value==None:
                item['auto'] = Database.beautify(item['name'])
                item['value'] = item['auto']
                value = item['auto']
            self._defined[item['name']] = {
                'name': item['name'],
                'value': item['value'],
                'auto': item['auto'],
                'type': item['type'],
                'source': item['source']
            }
        if item['name'] in self._items:
            item2 = self._items[item['name']]
            if 'locations' in item:
                item['locations'].append(self.item_location(item2))
                item2['locations'].append(self.item_location(item))
                locations = item2['locations']
                locations += item['locations']
                item2['locations'] = list(set(locations))
                self._items[item['name']] = item
            else:
                item2.update({
                    'value': item['value'],
                    'auto': item['auto']
                })
                item2['locations'].append(self.item_location(item))
            return
        if 'locations' in item:
            self._items[item['name']] = item
        else:
            self._items[item['name']] = item
            self._items[item['name']]['locations'] = [self.item_location(item)]

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
        for loc in item['locations']:
            if loc.startswith('PROGMEM_STRING_DEF:'):
                return True
        return False

    def rebuild_items(self):
        if self._target==None:
            return
        old = self.llen(self._items)
        self._items = {}
        for items in self._items_per_file.values():
            for item in items.values():
                self.merge(item)
        for item in self._defined.values():
            self.merge(item)
        new = self.llen(self._items)
        print('DEBUG rebuild items (old %u, %u -> new %u, %u)' % tuple(list(old) + list(new)))

    # remove the values from the current target
    def flush(self):
        if self._target==None:
            return
        if self.source_idx in self._items_per_file:
            print('DEBUG removing %u entries in %u locations' % self.llen(self._items_per_file[self.source_idx]));
            self._items_per_file[self.source_idx] = {}
            self.rebuild_items()

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
            if item['name']!=name:
                raise RuntimeError('invalid name %s!=%s' % (name, item['name']))
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
            item['locations'].append(self.item_location({'type': type, 'source': source}))
            item['locations'].append(self.item_location(item))
            item['locations'] = list(set(item['locations']))
            self.merge(item)
        else:
            items[name] = {
                'source': source,
                'name': name,
                'type': type,
                'value': value,
                'auto': auto_value,
                'locations': [],
                'vdb': False,
                'adb': False
            }
            items[name]['locations'].append(self.item_location(items[name]))
            self.merge(items[name])

    def item_location(self, item):
        return '%s:%s' % (item['type'], item['source'])

    # add items from preprocessor
    def add_items(self, items):
        if self._target==None:
            return
        for item in items:
            self.add(item.source_str, item.name, item.definition_type, item._value, item._auto)

        self.write();

    # write locations
    def write_locations(self, file: TextIOWrapper, item):
        loc = list(set(item['locations']))
        if self.config.locations_one_per_line:
            file.write('//' + '\n//'.join(loc))
        else:
            file.write('// %s\n' % ', '.join(loc))

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
        file.write('PROGMEM_STRING_DEF(%s, "%s"); // %s\n' % (item['name'], Database.split_hex(value), lang))

    def create_output_header(self, filename, extra_includes=None):
        if extra_includes and isinstance(extra_includes, str):
            extra_includes = [extra_includes]

        try:
            with open(filename, 'wt') as file:
                self._generator.write_header_comment(file)
                self._generator.write_header_start(file, extra_includes)
                for item in self._items.values():
                    if not self.is_static(item):
                        self.write_locations(file, item)
                        file.write('PROGMEM_STRING_DECL(%s);\n' % (item['name']))
                file.writelines([
                    '#ifdef __cplusplus\n',
                    '} // extern "C"\n',
                    '#endif\n'
                ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    def create_output_define(self, filename):
        count = 0
        try:
            with open(filename, 'wt') as file:
                self._generator.write_header_comment(file)
                file.write('#include "spgm_auto_strings.h"\n')
                for item in self._items.values():
                    if not self.is_static(item):
                        if item['name'] not in self._defined:
                            print('WARNING: cannot find %s in defined' % item['name'])
                        else:
                            defined = self._defined[item['name']]
                            if defined['value']!=item['value']:
                                raise RuntimeError('item %s defined does not match %s!=%s' % (item['name'], defined['value'], item['value']))
                        self.write_define(file, item)
                        count += 1
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return count

    def create_output_static(self, filename):
        try:
            with open(filename, 'wt') as file:
                self._generator.write_header_comment(file)
                for item in self._items.values():
                    if self.is_static(item):
                        self.write_define(file, item)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))



class Generator(object):

    def __init__(self, config: SpgmConfig, files: List[FS.File], target=None):
        self._config = config
        self._files = files
        self._items = [] # type: List[Item]
        self._merged = None
        self._language = {'default': 'default'} # type: Dict[str, List[str]]
        self._build = BuildDatabase()

        self._database_items = {} # type: Dict[str, Item]
        self._files_items = {} # type: Dict[str, Dict[FileLocation, Item]]
        self._build_items = {} # Dict[str, Dict[FileLocation, Item]]

        self._database = Database(self, target)
        self._database.read();

    # add items from preprocessor
    # gen.copy_to_database(fcpp.items)
    def copy_to_database(self, items):
        self._database.add_items(items)

    @property
    def config(self):
        return self._config

    @property
    def language(self):
        return self._language

    @property
    def files(self) -> List[FS.File]:
        return self._files

    @language.setter
    def language(self, language):
        lang = []
        if isinstance(language, str):
            lang = [l for l in language.split(',')]
        elif isinstance(language, (tuple, set, frozenset, list)):
            lang = list(language)
        if not 'default' in lang:
            lang.append('default')
        self._language = {}
        for lang in [l.strip('"\' \t\r\n') for l in lang if l.strip('"\' \t\r\n')]:
            lre = lang.lower()
            if '*' in lang or '_' in lang or '-' in lang:
                lre = re.sub('[_-]', '[_-]', lang.replace('*', '.*')) + r'\Z'
            self._language[lang] = lre

    def read_json_database(self, filename, build_filename):

        self._merged = None

        self._build.clear()
        if os.path.exists(build_filename):
            # SpgmConfig.debug('reading build database', True)
            try:
                with open(build_filename, 'rt') as file:
                    self._build._fromjson(json.loads(file.read()))
                # SpgmConfig.debug(self._build.__str__())
            except Exception as e:
                SpgmConfig.verbose('cannot read build database: %s' % e);

        if os.path.exists(filename):
            try:
                with open(filename, 'rt') as file:
                    contents = ''
                    for line in file.readlines():
                        line = line.strip()
                        if line.startswith('#') or line.startswith('//') or not line:
                            continue
                        contents += line + '\n'
                    if contents:
                        for name, data in json.loads(contents).items():
                            item = Item(name=name, lineno=ItemType.FROM_CONFIG, config_data=data)
                            if 'default' in data:
                                item._value = data['default']
                            elif 'auto' in data:
                                item._auto = data['auto']
                            if 'i18n' in data:
                                for lang, value in data['i18n'].items():
                                    item.i18n.set(lang, value)
                            if DebugType.DUMP_READ_CONFIG in Item.DEBUG:
                                print('read_json_database %s' % item)
                            # remove locations if build database does not contain an entry
                            locations = self._build.find(item.name)
                            if locations:
                                item._locations = locations.copy()
                            else:
                                item._locations = []
                            self._items.append(item)
            except RuntimeError as e:
                raise e
            except Exception as e:
                raise RuntimeError("cannot read %s: %s" % (filename, e))

    def write_json_database(self, filename, build_filename):

        if self._merged==None:
            self.merge_items(None)

        # create database
        out = {}
        trans = []
        for item in self._merged.values():
            item = item # type: Item
            val = {
                'use_counter': item.use_counter,
            }
            if item.has_value:
                val['default'] = item.value
                if item.has_auto_value:
                    raise RuntimeError('item has default and auto value: %s' % item)
            if item.has_auto_value:
                if item._auto!=None:
                    val['auto'] = item._auto
                else:
                    val['auto'] = item.beautify(item.name)
            for data in item.i18n_values:
                if not id(data) in trans:
                    if not 'i18n' in val:
                        val['i18n'] = {}
                    trans.append(id(data))
                    val['i18n'][';'.join(data.lang)] = data.value
            if item.has_locations:
                item._merge_build_locations(self._build)
                val['locations'] = item.get_locations_str(',')
            if item.static:
                val['type'] = 'static'
            elif item.is_from_source:
                val['type'] = 'source'
            out[item.name] = val
        try:
            with open(filename, 'wt') as file:
                contents = json.dumps(out, indent=4, sort_keys=True)
                file.write('// It is recommended to add strings to the source code using (F)SPGM, PROGMEM_STRING_DEF or AUTO_STRING_DEF instead of modifying this file\n')
                file.write(contents)
                if DebugType.DUMP_WRITE_CONFIG in Item.DEBUG:
                    print('contents', contents)

        except Exception as e:
            raise RuntimeError("cannot write %s: %s" % (filename, e))

        # update build database
        for item in self._merged.values():
            if item.use_counter:
                self._build.add(item)
        # SpgmConfig.debug('writing build database', True)
        # SpgmConfig.debug(str(self._build))

        with open(build_filename, 'wt') as file:
            file.write(self._build._tojson())


    def clear(self):
        pass


    def write_header_comment(self, file: TextIOWrapper):
        file.write("// AUTO GENERATED FILE - DO NOT MODIFY\n")

    def write_header_start(self, file: TextIOWrapper, extra_includes: List[str]):
        file.write('#pragma once\n')
        if extra_includes:
            for include_file in extra_includes:
                include_file = include_file.strip()
                if include_file and include_file.lower()!='none':
                    file.write('#include <%s>\n' % (include_file))
        file.writelines([
            '#ifdef __cplusplus\n',
            'extern "C" {\n',
            '#endif\n'
        ]);

    def write_locations(self, file: TextIOWrapper, item: Item):
        if item.has_locations:
            if self.config.locations_one_per_line:
                locations = self._build.merge_locations(item)
                file.write(item.get_locations_str(sep='', fmt='// %s\n', locations=locations))
            else:
                file.write('// %s\n' % item.locations_str)

    def write_define(self, file: TextIOWrapper, item: Item):
        p_lang, lang, value = item.get_value(self._language)
        self.write_locations(file, item)
        file.write('PROGMEM_STRING_DEF(%s, "%s"); // %s\n' % (item.name, Database.split_hex(value), lang))

    def create_output_header(self, filename, extra_includes=None):
        return self._database.create_output_header(filename, extra_includes)

        if extra_includes and isinstance(extra_includes, str):
            extra_includes = [extra_includes]

        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                self.write_header_start(file, extra_includes)
                for item in self._merged.values():
                    if item.is_from_source:
                    # if not item.static and (self._build.get(item.name) or (item.use_counter and item.type==ItemType.FROM_SOURCE)):
                        self.write_locations(file, item)
                        file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
                file.writelines([
                    '#ifdef __cplusplus\n',
                    '} // extern "C"\n',
                    '#endif\n'
                ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    def create_output_define(self, filename):
        return self._database.create_output_define(filename)
        count = 0
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                file.write('#include "spgm_auto_strings.h"\n')
                for item in self._merged.values():
                    if item.is_from_source:
                    # if not item.static and (self._build.get(item.name) or (item.use_counter and item.type==ItemType.FROM_SOURCE)):
                        self.write_define(file, item)
                        count += 1
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return count

    def create_output_static(self, filename):
        return self._database.create_output_static(filename)
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                for item in self._merged.values():
                    if item.static and item.type==ItemType.FROM_SOURCE:
                        self.write_define(file, item)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    def create_output_auto(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                for item in self._merged.values():
                    if item.has_auto_value:
                        pass
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))


    def find_items_by_name(self, item1: Item, types=(ItemType.FROM_SOURCE,), compare=None) -> Iterable[Item]:
        return (item2 for item2 in self.items if item1.is_type(item2, types) and (item1.name==item2.name) and (compare==None or compare(item1, item2)))

    def _compare_values(self):
        for item1 in self.items:
            for item2 in self.find_items_by_name(item1, compare=lambda item1, item2: (item1.type!=ItemType.FROM_CONFIG and item1.has_value and item2.has_value and item1.value!=item2.value)):
                raise RuntimeError('redefinition with different value %s="%s" in %s previous definition: "%s" in %s' % \
                    (item1.name, item1.value, item1.get_source(), item2.value, item2.get_source()))

    def _compare_i18n(self):
        for item1 in self.items:
            for item2 in (i for i in self.items if id(i)!=id(item1)):
                for d1 in item1.i18n_values:
                    for d2 in (d for d in item2.i18n_values if id(d)!=id(d1)):
                        if d1.value!=d2.value:
                            for lang in (l for l in d1.lang if l in d2.lang):
                                raise RuntimeError('redefinition with different i18n value %s="%s" in %s previous definition: "%s" in %s' % \
                                    (item1.name, d1.value, item1.get_source(), d2.value, item2.get_source()))

    def _merge_items(self, types=(ItemType.FROM_SOURCE,), merge_types=(ItemType.FROM_SOURCE,)):
        for item1 in (item for item in self.items if item.type in types):
            # add item to merged list
            if not item1.name in self._merged:
                if DebugType.DUMP_MERGE_ITEMS in Item.DEBUG:
                    print('merge create %s' % item1)
                self._merged[item1.name] = item1

            for item2 in (item for item in self.items if item.type in merge_types):
                if id(item1)==id(item2) or item1.name!=item2.name:
                    continue
            # # merge all other items into merged list
            # for item2 in self.find_items_by_name(item1, merge_types):
                # print notice if an item is defined multiple times

                # if item1.type!=ItemType.FROM_CONFIG and item2.type!=ItemType.FROM_CONFIG and item1.has_value and item2.has_value and item1.value==item2.value and item1.source_hash!=item2.source_hash:
                #     print('NOTICE: redefinition of %s="%s" in %s:%u first definition in %s:%u' % (item1.name, item2.name, item1.source, item1.lineno, item2.source, item2.lineno), file=sys.stderr)

                if DebugType.DUMP_MERGE_ITEMS in Item.DEBUG:
                    print('merge merge %s into %s' % (item2, item1))
                item1.merge(item2)
                self._merged[item1.name] = item1

                # item2.remove()
                self._items.remove(item2)

    def merge_items(self, items):
        if items:
            self._items.extend(items)

        self._merged = {}
        self._dump_grouped('start') # debug

        self._compare_values()
        self._compare_i18n()

        self._merge_items(types=(ItemType.FROM_SOURCE,), merge_types=(ItemType.FROM_SOURCE,))

        self._merge_items(types=(ItemType.FROM_CONFIG,), merge_types=(ItemType.FROM_BUILD_DATABASE,))

        self._merge_items(types=(ItemType.FROM_SOURCE,), merge_types=(ItemType.FROM_CONFIG,))


    def _dump(self, name):
        if DebugType.DUMP_ITEMS in Item.DEBUG:
            print('-'*76)
            print('%s:' % name)
            self.dump()
            print('-'*76)

    def _dump_merged(self, name):
        if DebugType.DUMP_ITEMS in Item.DEBUG:
            print('-'*76)
            print('%s:' % name)
            self.dump_merged()
            print('-'*76)

    def _dump_grouped(self, name):
        if DebugType.DUMP_ITEMS in Item.DEBUG:
            tmp = self._merged
            self._merged = {}
            for item in self.items:
                if not item.name in self._merged:
                    self._merged[item.name] = []
                self._merged[item.name].append(item)
            self._dump_merged(name)
            self._merged = tmp

    @property
    def items(self):
        return self._items

    def clear_items(self):
        self._items = []

    def dump(self):
        for item in self.items:
            print(str(item))

    def dump_merged(self):
        for item in self._merged.values():
            if isinstance(item, list):
                if item:
                    print(item[0].name)
                    for item2 in item:
                        print('  %s' % item2)
            else:
                print(str(item))

