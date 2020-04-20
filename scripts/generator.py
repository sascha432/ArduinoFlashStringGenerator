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
                    self.translate = json.loads(file.read())
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
            dir = os.path.dirname(os.path.realpath(sys.argv[0])) + os.sep
            template = None
            if type=='header':
                template = dir + '/header.h'
            elif type=='define':
                template = dir + '/definition.cpp'
            if template!=None:
                with open(template, 'rt') as file:
                    template = file.read()
        except:
            template = None
        try:
            with open(filename, 'wt') as file:
                file.write("// AUTO GENERATED FILE - DO NOT MODIFY\n")
                if template!=None:
                    file.write(template)
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

    def append_used(self, append_used):
        for item in append_used:
            value = item['value']
            name = value
            if not name in self.translate.keys():
                self.translate[name] = { 'use_counter': 0}
            self.translate[name]['use_counter'] = self.translate[name]['use_counter'] + 1
            if not name in self.locations.keys():
                self.locations[name] = []
            self.locations[name].append(item['file'] + ':' + str(item['line']))
            if not value in self.used.keys():
                self.used[value] = { 'name': name, 'value': value, 'static': False }

    def append_defined(self, append_defined):
        for item in append_defined:
            name = item['name']
            if name in self.defined.keys():
                item2 = self.defined[name]
                print("WARING: redefinition of " + name + '="' + name + '" in ' + item['file'] + ':' + str(item['line']) + ' first definition in ' + item2['file'] + ':' + str(item2['line']))
            else:
                item['static'] = True
                if name in self.translate.keys():
                    self.translate[name]['default'] = item['value']
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
        if name in self.translate.keys():
            trans = self.translate[name]
            if 'default' in trans.keys():
                return trans['default']
            elif 'auto' in trans.keys():
                return trans['auto']
        return item['value']
