#
# Author: sascha_lammers@gmx.de
#

try:
    from ..spgm_extra_script import SpgmExtraScript
except:
    pass
from io import TextIOWrapper
import pickle
try:
    from SCons.Node import FS
except:
    pass
import os
import json
import re
import pickle
from .types import ItemType, DebugType
from .item import Item
from .config import SpgmConfig
from .database2 import Database, v2
import generator
from .build_database import BuildDatabase
from typing import List, Dict, Iterable

setattr(generator, 'get_spgm_extra_script', lambda: generator.spgm_extra_script)

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


class Generator(object):

    def __init__(self, config: SpgmConfig, files, target=None):
        self._config = config
        self._files = files
        self._items = [] # type: List[Item]
        self._merged = None
        self._language = {'default': 'default'} # type: Dict[str, List[str]]
        self._build = BuildDatabase()

        if v2.database:
            self._database = v2.database
        else:
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
    def files(self):
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

    # def read_json_database(self, filename, build_filename):

    #     self._merged = None

    #     self._build.clear()
    #     if os.path.exists(build_filename):
    #         # SpgmConfig.debug('reading build database', True)
    #         try:
    #             with open(build_filename, 'rt') as file:
    #                 self._build._fromjson(json.loads(file.read()))
    #             # SpgmConfig.debug(self._build.__str__())
    #         except Exception as e:
    #             SpgmConfig.verbose('cannot read build database: %s' % e);

    #     if os.path.exists(filename):
    #         try:
    #             with open(filename, 'rt') as file:
    #                 contents = ''
    #                 for line in file.readlines():
    #                     line = line.strip()
    #                     if line.startswith('#') or line.startswith('//') or not line:
    #                         continue
    #                     contents += line + '\n'
    #                 if contents:
    #                     for name, data in json.loads(contents).items():
    #                         item = Item(name=name, lineno=ItemType.FROM_CONFIG, config_data=data)
    #                         if 'default' in data:
    #                             item._value = data['default']
    #                         elif 'auto' in data:
    #                             item._auto = data['auto']
    #                         if 'i18n' in data:
    #                             for lang, value in data['i18n'].items():
    #                                 item.i18n.set(lang, value)
    #                         if DebugType.DUMP_READ_CONFIG in Item.DEBUG:
    #                             print('read_json_database %s' % item)
    #                         # remove locations if build database does not contain an entry
    #                         locations = self._build.find(item.name)
    #                         if locations:
    #                             item._locations = locations.copy()
    #                         else:
    #                             item._locations = []
    #                         self._items.append(item)
    #         except RuntimeError as e:
    #             raise e
    #         except Exception as e:
    #             raise RuntimeError("cannot read %s: %s" % (filename, e))

    # def write_json_database(self, filename, build_filename):

    #     if self._merged==None:
    #         self.merge_items(None)

    #     # create database
    #     out = {}
    #     trans = []
    #     for item in self._merged.values():
    #         item = item # type: Item
    #         val = {
    #             'use_counter': item.use_counter,
    #         }
    #         if item.has_value:
    #             val['default'] = item.value
    #             if item.has_auto_value:
    #                 raise RuntimeError('item has default and auto value: %s' % item)
    #         if item.has_auto_value:
    #             if item._auto!=None:
    #                 val['auto'] = item._auto
    #             else:
    #                 val['auto'] = item.beautify(item.name)
    #         for data in item.i18n_values:
    #             if not id(data) in trans:
    #                 if not 'i18n' in val:
    #                     val['i18n'] = {}
    #                 trans.append(id(data))
    #                 val['i18n'][';'.join(data.lang)] = data.value
    #         if item.has_locations:
    #             item._merge_build_locations(self._build)
    #             val['locations'] = item.get_locations_str(',')
    #         if item.static:
    #             val['type'] = 'static'
    #         elif item.is_from_source:
    #             val['type'] = 'source'
    #         out[item.name] = val
    #     try:
    #         with open(filename, 'wt') as file:
    #             contents = json.dumps(out, indent=4, sort_keys=True)
    #             file.write('// It is recommended to add strings to the source code using (F)SPGM, PROGMEM_STRING_DEF or AUTO_STRING_DEF instead of modifying this file\n')
    #             file.write(contents)
    #             if DebugType.DUMP_WRITE_CONFIG in Item.DEBUG:
    #                 print('contents', contents)

    #     except Exception as e:
    #         raise RuntimeError("cannot write %s: %s" % (filename, e))

    #     # update build database
    #     for item in self._merged.values():
    #         if item.use_counter:
    #             self._build.add(item)
    #     # SpgmConfig.debug('writing build database', True)
    #     # SpgmConfig.debug(str(self._build))

    #     with open(build_filename, 'wt') as file:
    #         file.write(self._build._tojson())

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

    def create_output_header(self, filename, extra_includes=None):
        if extra_includes and isinstance(extra_includes, str):
            extra_includes = [extra_includes]

        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                self.write_header_start(file, extra_includes)
                for item in self._database.get_items().values():
                    self._database.write_locations(file, item)
                    file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
                file.writelines([
                    '#ifdef __cplusplus\n',
                    '} // extern "C"\n',
                    '#endif\n'
                ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))


        # if extra_includes and isinstance(extra_includes, str):
        #     extra_includes = [extra_includes]

        # try:
        #     with open(filename, 'wt') as file:
        #         self.write_header_comment(file)
        #         self.write_header_start(file, extra_includes)
        #         for item in self._merged.values():
        #             if item.is_from_source:
        #             # if not item.static and (self._build.get(item.name) or (item.use_counter and item.type==ItemType.FROM_SOURCE)):
        #                 self.write_locations(file, item)
        #                 file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
        #         file.writelines([
        #             '#ifdef __cplusplus\n',
        #             '} // extern "C"\n',
        #             '#endif\n'
        #         ])
        # except OSError as e:
        #     raise RuntimeError("cannot create %s: %s" % (filename, e))

    def create_output_define(self, filename):
        count = 0
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                file.write('#include "spgm_auto_strings.h"\n')
                for item in self._database.get_items().values():
                    # if item in self.get_items().values():
                    #     if defined['value']!=item['value']:
                    #         raise RuntimeError('item %s defined does not match %s!=%s' % (item.name, defined['value'], item['value']))
                    self._database.write_define(file, item)
                    count += 1
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return count

    def create_output_static(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                for item in self._database.get_static_items().values():
                    self._database.write_define(file, item)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    # def create_output_auto(self, filename):
    #     try:
    #         with open(filename, 'wt') as file:
    #             self.write_header_comment(file)
    #             for item in self._merged.values():
    #                 if item.has_auto_value:
    #                     pass
    #     except OSError as e:
    #         raise RuntimeError("cannot create %s: %s" % (filename, e))


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

