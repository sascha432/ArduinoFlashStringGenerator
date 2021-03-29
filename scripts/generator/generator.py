#
# Author: sascha_lammers@gmx.de
#

try:
    from ..spgm_extra_script import SpgmExtraScript
except:
    pass
from io import TextIOWrapper
try:
    from SCons.Node import FS
except:
    pass
import re
import pickle
from .item import Item
from .config import SpgmConfig
from .database2 import Database
import generator
from typing import List, Dict

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

    def __init__(self, config: SpgmConfig, files, target, env):
        self._env = env
        self._config = config
        self._files = files
        self._language = {'default': 'default'} # type: Dict[str, List[str]]
        self._database = Database(self, target)


    def read_database(self):
        self._database.read();

    # add items from preprocessor
    # gen.copy_to_database(fcpp.items)
    def copy_to_database(self, items):
        self._database.flush()
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

    def write_header_comment(self, file: TextIOWrapper):
        print("// AUTO GENERATED FILE - DO NOT MODIFY", file=file)

    def write_header_start(self, file: TextIOWrapper, extra_includes: List[str]):
        print('#pragma once', file=file)
        if extra_includes:
            for include_file in extra_includes:
                include_file = include_file.strip()
                if include_file and include_file.lower()!='none':
                    print('#include <%s>' % include_file, file=file)
        file.writelines([
            '#ifdef __cplusplus\n',
            'extern "C" {\n',
            '#endif\n'
        ]);

    # create declarations header
    # default: spgm_auto_strings.h
    def create_output_header(self, filename, extra_includes=None):
        if extra_includes and isinstance(extra_includes, str):
            extra_includes = [extra_includes]

        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                self.write_header_start(file, extra_includes)
                for item in self._database.get_items().values():
                    if self.config.add_unused or self._database.is_used(item):
                        self._database.write_locations(file, item)
                        file.write('PROGMEM_STRING_DECL(%s);\n' % (item.name))
                file.writelines([
                    '#ifdef __cplusplus\n',
                    '} // extern "C"\n',
                    '#endif\n'
                ])
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    # create defintions for the strings
    # default: spgm_auto_strings.cpp
    def create_output_define(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                print('#include "spgm_auto_strings.h"', file=file)
                values = self._database.get_items().values()
                for item in values:
                    if self.config.add_unused or self._database.is_used(item):
                        self._database.write_define(file, item)
                return len(values)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
        return 0

    # create a list of statically defined strings
    # default: spgm_static_strings.h
    def create_output_static(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                print('#include <spgm_string_generator.h>', file=file)
                for item in self._database.get_static_items().values():
                    self._database.write_define(file, item, True)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))

    # create a list of automatically defined strings
    # default: spgm_auto_defined.h
    def create_output_auto_defined(self, filename):
        try:
            with open(filename, 'wt') as file:
                self.write_header_comment(file)
                print('#include <spgm_string_generator.h>', file=file)
                print('FLASH_STRING_GENERATOR_AUTO_INIT(', file=file)
                for item in self._database.get_items().values():
                    if not item.has_value:
                        self._database.write_auto_init(file, item)
                print(')', file=file)
        except OSError as e:
            raise RuntimeError("cannot create %s: %s" % (filename, e))
