#
# Author: sascha_lammers@gmx.de
#

import sys
import os
import json
import copy
from .item import Item

class Generator:

    def __init__(self):
        self._items = []
        self._merged = {}
        # self.translate = {}
        # self.defined = {}
        # self.used = {}
        # self.locations = {}

    def beautify(self, name):
        name = name.replace('_', ' ')
        return name

    def read_config_json(self, filename):
        self.translate = {}
        if os.path.exists(filename):
            try:
                with open(filename, 'rt') as file:
                    contents = file.read().strip();
                    if contents:
                        for name, data in json.loads(contents).items():
                            item = Item(name=name)
                            if 'default' in data:
                                item._value = data['default']
                            elif 'auto' in data:
                                item._value = data['auto']
                                item.auto = True
                            if 'i18n' in data:
                                for lang, value in data['i18n'].items():
                                    item.i18n.set(lang, value)
                            self._items.append(item)
            except Exception as e:
                raise RuntimeError("cannot read %s: %s" % (filename, e))

        # reset counters
        for name in self.translate:
            self.translate[name]['use_counter'] = 0

    def write_config_json(self, filename):
        try:
            with open(filename, 'wt') as file:
                # file.write(json.dumps(self.translate, indent=4))
                pass
        except Exception as e:
            raise RuntimeError("cannot write %s: %s" % (filename, e))

    def write(self, filename, type, include_file = None):
        # if type=='static':
        #     items = self.defined
        # else:
        #     items = self.used
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
                for item in self._merged.values():
                    if item.is_valid and not item.removed and (type=='static')==item.static:
                        name = item.name
                    # item = items[string]
                    # if (type=='static' and item['static']==True) or item['static']==False:
                        # name = item['name']
                        # if name in self.locations:
                        #     for location in self.locations[name]:

                        if item.locations:
                            file.write('// %s' % item.locations_str)
                        num = num + 1
                        if type=='header':
                            file.write('PROGMEM_STRING_DECL(%s);\n' % (name))
                        else:
                            file.write('PROGMEM_STRING_DEF(%s, "%s");\n' % (name, item.value))
                if type=="header":
                    file.writelines([
                        '#ifdef __cplusplus\n',
                        '} // extern "C"\n',
                        '#endif\n'
                    ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return num

    def find_items(self, name, item_self=None, return_removed=False):
        return [item for item in self._items if (return_removed or not item.removed) and (item.name==name) and (item_self==None or id(item)!=id(item_self))]

    def find_lang(self, name, lang, item_self=None):
        for item in self.find_items(name, item_self):
            res = item.i18n.find(lang)
            if res:
                return res
        return None

    def merge_items(self, items):
        self._merged = {}
        for item in items:
            if item.removed:
                continue
            for item2 in self.find_items(item.name, item, True):

                # print("N",item2.name,item2._use_counter)
                # print("X",item2)

                # check if the item is defined multiple times
                if not item2.removed and not item.from_config_file and not item2.from_config_file and item.type in(Item.ItemType.DEFINE, Item.ItemType.AUTO_INIT) and item2:
                    print('WARNING: redefinition of %s="%s" in %s:%u first definition in %s:%u' % (item.name, item2.name, item.source, item.lineno, item2.source, item2.lineno))

                # check for invalid redefinitions and merge default values
                cmp_item = self.compare_values(item, item2)
                if cmp_item:
                    raise RuntimeError('redefinition with different value %s="%s" in %s:%u previous definition: "%s" in %s:%u' % \
                        (item.name, item.value, item.source, item.lineno, \
                        cmp_item.value, item2.source, item2.lineno))

                # # TODO remove debug code
                # item = copy.deepcopy(item)
                # item2 = copy.deepcopy(item2)

                item.merge(item2)

                if item.has_use_counter:
                    if item.type==Item.ItemType.SPGM:
                        item.use_counter += 1
                    if item2.has_use_counter:
                        item.copy_counter(item2)

                if item.has_locations and item2.has_locations:
                    item.copy_locations(item2)

                self._merged[item.name] = item

            # add item to list
            self._items.append(item)

    def compare_values(self, item1, item2):
        if item1.removed or item2.removed or \
                item1.from_config_file or item2.from_config_file or \
                item1==item2:
            return None
        if item1.has_value and item2.has_value and item1._value!=item2._value:
            return item2
        for l1, i1 in item1.i18n.items():
            for l2, i2 in item2.i18n.items():
                # //TODO
                print(l1,l2,i1,i2)
        return None

    def update_items(self):
        # check for missing values and add if possible
        for item in self._items:
            if item.removed:
                continue
            if item.value==None:
                for item2 in self.find_items(item.name, item):
                    if item2.value!=None:
                        item.value = item2.value
                        break
        # create values automatically and mark them
        for item in self._items:
            if item.value==None:
                item.value = self.beautify(item.name)
                item.auto = True

    @property
    def items(self):
        return self._items

    def clear_items(self):
        self._items = {}

    def dump(self):
        for item in self._items:
            print(str(item))

    def dump_merged(self):
        for item in self._merged.values():
            print(str(item))

    # def use_counter(self, name):
    #     n = 0
    #     for item in self._items:
    #         if item.unused==False and item.type==self.SPGM and item.name==name:
    #             n += 1
    #     return n

    # def get_value(self, item):
    #     name = item.name
    #     if item.default_value!=None:
    #         return item.default_value
    #     if name in self.translate.keys():
    #         trans = self.translate[name]
    #         if 'default' in trans.keys():
    #             return trans['default']
    #         elif 'auto' in trans.keys():
    #             return trans['auto']
    #     return item['value']
