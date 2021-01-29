#
# Author: sascha_lammers@gmx.de
#

try:
    from ..spgm_extra_script import SpgmExtraScript
except:
    pass
from io import TextIOWrapper
from SCons.Node import FS
import sys
import os
import json
import typing
import re
from .item import Item, ItemType, DefinitionType, DebugType, i18n
from .config import SpgmConfig
import enum
import generator
from .item import Item, Location
from typing import List, Dict, Iterable, Any, Union

# def get_spgm_extra_script():
#     return generator.spgm_extra_script

setattr(generator, 'get_spgm_extra_script', lambda: generator.spgm_extra_script)

class FilterType(enum.Enum):
    NO_MATCH = 'NO_MATCH'
    INCLUDE = 'INCLUDE'
    EXCLUDE = 'EXCLUDE'

    def __str__(self):
        return str(self.value)

class BuildDatabase(object):

    def __init__(self, locations=None):
        self._items = {} # type: Dict[str, List[Location]]
        if locations:
            self._fromjson(locations)

    def set(self, item: Item):
        self._items[item.name] = item.locations

    def add(self, item: Item):
        if item.name in self._items:
            self._items[item.name] = Item._merge_locations(self._items[item.name], item.locations)
        else:
            self._items[item.name] = item.locations

    def get(self, name):
        if name in self._items:
            return self._items[name]
        return None

    def clear(self):
        self._items = {}

    def merge_items(self, items):
        SpgmConfig.debug('merge_items', True)
        for name, locations in self._items.items():
            SpgmConfig.debug('name %s locations %s' % (name, locations))
            result = [(idx, i) for idx, i in enumerate(items) if i.name==name]
            if len(result)!=1:
                raise RuntimeError('item does not exist: name=%s items=%s result=%s' % (name, [str(i) for i in items], result))
            self._items[name] = Item._merge_locations(items[result[0][0]].locations, locations)
            # for location in locations.values():
            #     if not item._locations.find(Location):
            #         SpgmConfig.debug('item %s: append location=%s' % (name, location))
            #         item._locations.append(location)


    def _fromjson(self, locations):
        for name, locations in locations.items():
            locations = [l for l in [Location(*location) for location in locations] if l.lineno>=0]
            self._items[name] = Item._merge_locations(name in self._items and self._items[name] or [], locations)

    def _tojson(self, indent=0):
        indent = ' '*indent
        keys = [item[0] for item in self._items.items() if item[1]]
        values = [list(map(lambda location: location._totuple(), locations)) for name, locations in self._items.items() if locations]
        return json.dumps(dict(zip(keys, values))).replace('{"', '{\n%s"' % indent).replace(']], "', ']],\n%s"' % indent).replace(']}', ']\n}')

    def __str__(self):
        return re.sub('((\[\[)|(\[)|\]\]|\])', lambda arg: (arg.group(1)=='[[' and '[(' or (arg.group(1)==']]' and ')]' or arg.group(1)=='[' and '(' or ')')), self._tojson().replace(']], "', ']],\n"')[2:-2])


class Generator(object):

    def __init__(self, config: SpgmConfig, files: List[FS.File]):
        self._config = config
        self._files = files
        self._items = [] # type: List[Item]
        self._merged = {} # type: Dict[str, Item]
        self._language = {'default': 'default'} # type: Dict[str, List[str]]
        self._build = BuildDatabase()

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

    @property
    def merged_items(self):
        values = self._merged.values() # type: List[Union[Item, List[Item]]]
        return values

    def read_json_database(self, filename, build_filename):

        self._build.clear()
        if os.path.exists(build_filename):
            SpgmConfig.debug('reading build database', True)
            with open(build_filename, 'rt') as file:
                self._build._fromjson(json.loads(file.read()))
            SpgmConfig.debug(self._build.__str__())

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
                            self._items.append(item)
            except RuntimeError as e:
                raise e
            except Exception as e:
                import time#TODO remove
                time.sleep(5)
                raise RuntimeError("cannot read %s: %s" % (filename, e))

            self._build.merge_items(self._items)

    def write_json_database(self, filename, build_filename):

        # update build database
        for item in self.merged_items:
            if item.use_counter:
                self._build.add(item)
        SpgmConfig.debug('writing build database', True)
        SpgmConfig.debug(str(self._build))

        with open(build_filename, 'wt') as file:
            file.write(self._build._tojson(indent=4))

        # create database
        out = {}
        trans = []
        for item in self.merged_items:
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
                val['locations'] = item.get_locations_str(',')
            out[item.name] = val

        try:
            with open(filename, 'wt') as file:
                contents = json.dumps(out, indent=4)
                file.write('// It is recommended to add strings to the source code using (F)SPGM, PROGMEM_STRING_DEF or AUTO_STRING_DEF instead of modifying this file\n')
                file.write(contents)
                if DebugType.DUMP_WRITE_CONFIG in Item.DEBUG:
                    print('contents', contents)

        except Exception as e:
            raise RuntimeError("cannot write %s: %s" % (filename, e))

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
                locations = item.locations
                build_locations = self._build.get(item.name)
                if build_locations:
                    locations = Item._merge_locations(build_locations.copy(), locations)
                file.write(item.get_locations_str(sep='', fmt='// %s\n', locations=locations))
            else:
                file.write('// %s\n' % item.locations_str)

    def write_define(self, file: TextIOWrapper, item: Item):
        p_lang, lang, value = item.get_value(self._language)
        self.write_locations(file, item)
        file.write('PROGMEM_STRING_DEF(%s, "%s"); // %s\n' % (item.name, value, lang))

    def create_output_header(self, filename, extra_includes=None):
        if extra_includes and isinstance(extra_includes, str):
            extra_includes = [extra_includes]
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                self.write_header_start(file, extra_includes)
                for item in self._merged.values():
                    if self._build.get(item.name) or (item.use_counter and item.type==ItemType.FROM_SOURCE):
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
        count = 0
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                file.write('#include "spgm_auto_strings.h"\n')
                for item in self.merged_items:
                    if self._build.get(item.name) or (item.use_counter and item.type==ItemType.FROM_SOURCE):
                        self.write_define(file, item)
                        count += 1
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return count

    def create_output_static(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                for item in self.merged_items:
                    if item.static and item.type==ItemType.FROM_SOURCE:
                        self.write_define(file, item)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    def create_output_auto(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                for item in self.merged_items:
                    if item.has_auto_value:
                        pass
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    # def write(self, filename, type, include_file=None):
    #     num = 0
    #     try:
    #         with open(filename, 'wt') as file:
    #             self.write_header_comment(file)

    #             if type=='header':
    #                 self.write_header_start(file, [include_file])
    #             elif type=='define':
    #                 file.write('#include "FlashStringGeneratorAuto.h"\n')

    #             for item in self._merged.values():
    #                 if type=='static' and not item.static:
    #                     continue
    #                 if item.type==ItemType.FROM_SOURCE:
    #                     p_lang, lang, value = item.get_value(self._language)
    #                     if item.has_locations:
    #                         if self.config.locations_one_per_line:
    #                             file.write(item.get_locations_str(sep='', fmt='// %s\n'))
    #                         else:
    #                             file.write('// %s\n' % item.locations_str)
    #                     num = num + 1
    #                     if type=='header':
    #                         file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
    #                     else:
    #                         file.write('PROGMEM_STRING_DEF(%s, "%s"); // %s\n' % (item.name, value, lang))
    #                 # else:
    #                 #     print('skipped %s' % item)

    #             if type=="header":
    #                 file.writelines([
    #                     '#ifdef __cplusplus\n',
    #                     '} // extern "C"\n',
    #                     '#endif\n'
    #                 ])
    #     except OSError as e:
    #         raise RuntimeError("cannot create %s: %s" % (filename, e))
    #     return num

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

            # merge all other items into merged list
            for item2 in self.find_items_by_name(item1, merge_types):
                # print notice if an item is defined multiple times
                if item1.type!=ItemType.FROM_CONFIG and item2.type!=ItemType.FROM_CONFIG and item1.has_value and item2.has_value and item1.value==item2.value:
                    print('NOTICE: redefinition of %s="%s" in %s:%u first definition in %s:%u' % (item1.name, item2.name, item1.source, item1.lineno, item2.source, item2.lineno), file=sys.stderr)

                if DebugType.DUMP_MERGE_ITEMS in Item.DEBUG:
                    print('merge merge %s into %s' % (item2, item1))
                item1.merge(item2)
                self._merged[item1.name] = item1

                # item2.remove()
                self._items.remove(item2)

    def merge_items(self, items):
        self._items.extend(items)
        self._merged = {}
        self._dump_grouped('start') # debug

        self._compare_values()
        self._compare_i18n()

        # merge items from source first and override everything from the config file
        self._merge_items()
        self._dump_merged('_merge_items') # debug

        # merge items from config
        self._merge_items(types=(ItemType.FROM_SOURCE,), merge_types=(ItemType.FROM_CONFIG,))
        self._dump_merged('after _merge_items_from_config') # debug

        self._merge_items(types=(ItemType.FROM_CONFIG,), merge_types=(ItemType.FROM_SOURCE,))
        self._dump_merged('after _merge_items_to_config') # debug

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
        for item in self.merged_items:
            if isinstance(item, list):
                if item:
                    print(item[0].name)
                    for item2 in item:
                        print('  %s' % item2)
            else:
                print(str(item))

