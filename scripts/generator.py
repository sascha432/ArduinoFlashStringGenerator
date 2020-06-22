#
# Author: sascha_lammers@gmx.de
#

import sys
import os
import json

class Generator:
    def __init__(self):
        self.translate = {}
        self.defined = {}
        self.used = {}
        self.locations = {}

    def beatify(self, name):
        name = name.replace('_', ' ')
        return name

    def read_translate(self, filename):
        self.translate = {}
        if os.path.exists(filename):
            try:
                with open(filename, 'rt') as file:
                    contents = file.read().strip();
                    if contents:
                        self.translate = json.loads(contents)
            except Exception as e:
                print(filename + ": Cannot read file")
                print(e)
                sys.exit(1)
        # reset counters
        for name in self.translate:
            self.translate[name]['use_counter'] = 0

    def write_translate(self, filename):
        try:
            with open(filename, 'wt') as file:
                file.write(json.dumps(self.translate, indent=4))
        except:
            print(filename + ': Cannot write file')
            sys.exit(1)

    def write(self, filename, type, include_file = None):
        if type=='static':
            items = self.defined
        else:
            items = self.used
        num = 0
        try:
            with open(filename, 'wt') as file:
                file.write("// AUTO GENERATED FILE - DO NOT MODIFY\n")
                if type=='header':
                    file.write('#pragma once\n')
                if type=='define' or type=='header':
                    if include_file!='' and include_file.lower()!='none':
                        file.write('#include <' + include_file + '>\n')
                for string in items:
                    item = items[string]
                    if (type=='static' and item['static']==True) or item['static']==False:
                        name = item['name']
                        if name in self.locations.keys():
                            for location in self.locations[name]:
                                file.write('// ' + location  + '\n')
                        num = num + 1
                        if type=='header':
                            file.write('PROGMEM_STRING_DECL(' + name + ');\n')
                        else:
                            file.write('PROGMEM_STRING_DEF(' + name + ', "' + self.get_value(item) + '");\n')
        except OSError as e:
            print(filename + ': Cannot create file')
            sys.exit(1)
        return num

    def compare_defaults(self, prev, item):
        if 'default' in prev and 'default' in item and prev['default']!=item['default']:
            raise RuntimeError("Invalid redefinition of %s: %s:%u: '%s' != '%s'" % (name, item['file'], int(item['line']), item['default'], prev['default']))
        if 'i18n' in prev:
            for lang in prev['i18n']:
                try:
                    if item['i18n'][lang]!=prev['i18n'][lang]:
                        raise RuntimeError("Invalid redefinition of %s: %s:%u: '%s' != '%s'" % (name, item['file'], int(item['line']), item['i18n'][lang], prev['i18n'][lang]))
                except Exception as e:
                    print(e)


    def merge_item(self, val1, val2):
        if 'default' in val2:
            val1['default'] = val2['default']
            if 'auto' in val1:
                del val1['auto']
        if 'i18n' in val2:
            val1['i18n'] = val2['i18n']
        return val1

    def append_used(self, append_used):
        for item in append_used:
            value = item['value']
            name = value
            # add counter for new items and merge defaults
            if not name in self.translate.keys():
                self.translate[name] = { 'use_counter': 0 }
            self.translate[name]['use_counter'] = self.translate[name]['use_counter'] + 1
            self.translate[name] = self.merge_item(self.translate[name], item)

            # add location of the define
            if not name in self.locations.keys():
                self.locations[name] = []
            self.locations[name].append(item['file'] + ':' + str(item['line']))

            if not value in self.used.keys():
                self.used[value] = self.merge_item({ 'name': name, 'value': value, 'static': False }, item)
            else:
                self.compare_defaults(self.used[value], item)

    def append_defined(self, append_defined):
        for item in append_defined:
            name = item['name']
            if name in self.defined.keys():
                item2 = self.defined[name]
                print("WARING: redefinition of " + name + '="' + name + '" in ' + item['file'] + ':' + str(item['line']) + ' first definition in ' + item2['file'] + ':' + str(item2['line']))
            else:
                item['static'] = True
                if name in self.translate.keys():
                    trans = self.translate[name]
                    # if 'default' in trans and trans['default']!=item['value']:
                    #     print("WARNING! xxx")
                    trans['default'] = item['value']
                self.defined[name] = item

    def update_statics(self):
        for item in self.used:
            name = self.used[item]['name']
            if name in self.defined.keys():
                self.used[item]['static'] = True
            else:
                if name in self.translate.keys():
                    trans = self.translate[name]
                    if not 'default' in trans.keys():
                        trans['auto'] = self.beatify(self.used[item]['value'])

    def get_used(self):
        return self.used

    def get_defined(self):
        return self.defined

    def get_value(self, item):
        name = item['name']
        if 'default' in item:
            return item['default']
        if name in self.translate.keys():
            trans = self.translate[name]
            if 'default' in trans.keys():
                return trans['default']
            elif 'auto' in trans.keys():
                return trans['auto']
        return item['value']