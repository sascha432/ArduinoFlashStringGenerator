#
# Author: sascha_lammers@gmx.de
#

import sys
import os
import json
import copy
from typing import Iterable
from .item import Item, ItemType, DefinitionType, DebugType

class Generator:

    def __init__(self):
        self._items = []
        self._merged = {}
        self._config = {
            'locations_one_per_line': False
        }

    @property
    def config_locations_one_per_line(self):
        return self._config['locations_one_per_line']

    def read_config_json(self, filename):
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
                            if name=='__FLASH_STRING_GENERATOR_CONFIG__':
                                for key, val in data.items():
                                    if not key in self._config:
                                        raise RuntimeError('invalid configuration key: %s: %s' % (key, filename))
                                    if type(val)!=type(self._config[key]):
                                        raise RuntimeError('invalid configuration key: %s: type: %s: expected: %s: %s' % (key, type(val), type(self._config[key]), filename))
                                    self._config[key] = val
                                continue
                            item = Item(name=name, lineno=ItemType.FROM_CONFIG, config_data=data)
                            if 'default' in data:
                                item._value = data['default']
                            elif 'auto' in data:
                                item._auto = data['auto']
                            if 'i18n' in data:
                                for lang, value in data['i18n'].items():
                                    item.i18n.set(lang, value)
                            if DebugType.DUMP_READ_CONFIG in Item.DEBUG:
                                print('read_config_json %s' % item)
                            self._items.append(item)
            except RuntimeError as e:
                raise e
            except Exception as e:
                raise RuntimeError("cannot read %s: %s" % (filename, e))

    def write_config_json(self, filename):
        out = {
            '__FLASH_STRING_GENERATOR_CONFIG__': self._config
        }
        trans = []
        for item in self._merged.values():
            val = {
                'use_counter': item.use_counter,
            }
            if item.has_value:
                val['default'] = item.value
            if item.auto_value:
                if item._auto!=None:
                    val['auto'] = item._auto
                else:
                    val['auto'] = item.beautify(item.name)
            for data in item.i18n.values():
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
                    print(contents)

        except Exception as e:
            raise RuntimeError("cannot write %s: %s" % (filename, e))

    def write(self, filename, type, include_file = None):
        num = 0
        try:
            with open(filename, 'wt') as file:
                file.write("// AUTO GENERATED FILE - DO NOT MODIFY\n")
                if type=='header':
                    if include_file!='' and include_file.lower()!='none':
                        file.write('#include <' + include_file + '>\n')
                    file.writelines([
                        '#pragma once\n',
                        '#ifdef __cplusplus\n',
                        'extern "C" {\n',
                        '#endif\n'
                    ])
                elif type=='define':
                    file.write('#include "FlashStringGeneratorAuto.h"\n')

                for item in (i for i in self._merged.values() if type=='static' or i.static):
                   if item.type==ItemType.FROM_SOURCE:
                        if item.has_locations:
                            if self.config_locations_one_per_line:
                                file.write(item.get_locations_str(sep='', fmt='// %s\n'))
                            else:
                                file.write('// %s\n' % item.locations_str)
                        num = num + 1
                        if type=='header':
                            file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
                        else:
                            file.write('PROGMEM_STRING_DEF(%s, "%s");\n' % (item.name, item.value))

                if type=="header":
                    file.writelines([
                        '#ifdef __cplusplus\n',
                        '} // extern "C"\n',
                        '#endif\n'
                    ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return num

    def find_items_by_name(self, item1, types=(ItemType.FROM_SOURCE,), compare=None) -> Iterable[Item]:
        return (item2 for item2 in self.items if item1.is_type(item2, types) and (item1.name==item2.name) and (compare==None or compare(item1, item2)))

    def _compare_values(self):
        for item1 in self.items:
            for item2 in self.find_items_by_name(item1, compare=lambda item1, item2: (item1.type!=ItemType.FROM_CONFIG and item1.has_value and item2.has_value and item1.value!=item2.value)):
                raise RuntimeError('redefinition with different value %s="%s" in %s previous definition: "%s" in %s' % \
                    (item1.name, item1.value, item1.get_source(), item2.value, item2.get_source()))

    def _compare_i18n(self):
        for item1 in self.items:
            for item2 in (i for i in self.items if id(i)!=id(item1)):
                for d1 in item1.i18n.values():
                    for d2 in (d for d in item2.i18n.values() if id(d)!=id(d1)):
                        if d1.value!=d2.value:
                            for lang in (l for l in d1.lang if l in d2.lang):
                                raise RuntimeError('redefinition with different i18n value %s="%s" in %s previous definition: "%s" in %s' % \
                                    (item1.name, d1.value, item1.get_source(), d2.value, item2.get_source()))

    def _merge_items(self, types=(ItemType.FROM_SOURCE,), merge_types=(ItemType.FROM_SOURCE,)):
        for item1 in (item for item in self.items if item.type in types):
            # if not item1.type in types:
            #     continue

            # add item to merged list
            if not item1.name in self._merged:
                if DebugType.DUMP_MERGE_ITEMS in Item.DEBUG:
                    print('merge create %s' % item1)
                self._merged[item1.name] = item1

            # merge all other items into merged list
            for item2 in self.find_items_by_name(item1, merge_types):
                # print notice if an item is defined multiple times
                if item1.type!=ItemType.FROM_CONFIG and item2.type!=ItemType.FROM_CONFIG and item1.has_value and item2.has_value and item1.value==item2.value:
                    print('NOTICE: redefinition of %s="%s" in %s:%u first definition in %s:%u' % (item1.name, item2.name, item1.source, item1.lineno, item2.source, item2.lineno))

                if DebugType.DUMP_MERGE_ITEMS in Item.DEBUG:
                    print('merge merge %s into %s' % (item2, item1))
                item1.merge(item2)
                self._merged[item1.name] = item1

                # item2.remove()
                self._items.remove(item2)

    # def _update_items(self):
    #     # check for missing values and add if possible
    #     for item1 in self.items:
    #         if item1.type in(ItemType.FROM_SOURCE, ItemType.FROM_CONFIG) and item1.value==None:
    #             for item2 in self.find_items_by_name(item1):
    #                 if item2.value!=None:
    #                     raise RuntimeError('item without value %s: %s' % (item2, item1))

    def merge_items(self, items):
        self._items.extend(items)
        self._merged = {}
        self._dump_grouped('start')

        # self._remove_auto_values_and_fill_blanks()
        # self._dump_grouped('after _remove_auto_values_and_fill_blanks')

        self._compare_values()
        self._compare_i18n()

        # merge items from source first and override everything from the config file
        self._merge_items()
        self._dump_merged('_merge_items')

        # merge items from config
        self._merge_items(types=(ItemType.FROM_CONFIG,), merge_types=(ItemType.FROM_CONFIG,))
        self._dump_merged('after _merge_items_from_config')

        # self._update_items()
        # self._dump_merged('after _update_items')

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
    def items(self) -> Iterable[Item]:
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
