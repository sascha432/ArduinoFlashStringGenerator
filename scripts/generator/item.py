#
# Author: sascha_lammers@gmx.de
#

import os
import copy
import enum
import re
from typing import List, Tuple, Union
from .config import SpgmConfig

DEFAULT_LANGUAGE = 'default'

class ItemType(enum.Enum):
    FROM_SOURCE = 0
    FROM_CONFIG = -1
    REMOVED = -2
    FROM_BUILD_DATABASE = -3

    def __str__(self):
        return str(self).split('.')[-1]

class DefinitionType(enum.Enum):
    DEFINE = 'DEFINE'
    SPGM = 'SPGM'
    AUTO_INIT = 'AUTO_INIT'

    def __str__(self):
        if self==DefinitionType.DEFINE:
            return 'PROGMEM_STRING_DEF'
        if self==DefinitionType.AUTO_INIT:
            return 'AUTO_STRING_DEF'
        return str(self.value).split('.')[-1]

class DebugType(enum.Enum):
    TOKEN = 'token'
    PUSH_VALUE = 'push_value'
    DUMP_ITEMS = 'dump_items'
    EXCEPTION = 'exception'
    ITEM_DEBUG_ATTR = 'item_debug_attr'
    DUMP_READ_CONFIG = 'dump_read_config'
    DUMP_WRITE_CONFIG = 'dump_write_config'
    DUMP_MERGE_ITEMS = 'dump_merge_items'

ITEM_DEBUG = frozenset([DebugType.EXCEPTION])

class SourceType(enum.Enum):
    REL_PATH = 'rel'
    ABS_PATH = 'abs'
    REAL_PATH = 'real'
    FILENAME = 'filename'

class Location(object):
    def __init__(self, source, lineno, definition_type='REMOVED'):
        self.source = source
        self.lineno = lineno
        self.definition_type = DefinitionType(definition_type)

    def format(self, fmt):
        return fmt % ('%s:%s (%s)' % (self.source, self.lineno, self.definition_type.value))

    def __eq__(self, o: object) -> bool:
        return id(self)==id(o) or (isinstance(self.lineno, int) and isinstance(o.lineno, int) and self.source==o.source and self.lineno==o.lineno)

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        # if isinstance(self.lineno, ItemType):
        #     if self.lineno==ItemType.FROM_SOURCE:
        #         return '<source>'
        #     elif self.lineno==ItemType.FROM_CONFIG:
        #         return '<config>'
        #     elif self.lineno==ItemType.REMOVED:
        #         return '<removed>'
        return str(tuple([self.source, str(self.lineno), str(self.definition_type.value)]))

    def __hash__(self):
        return hash('%s;%s;%s;%s' % (id(self), self.source, self.lineno, self.definition_type.value))

    def _totuple(self):
        return (self.source, int(self.lineno), str(self.definition_type.value))

class SourceLocation(object):

    display_source = SourceType.REL_PATH

    def __init__(self, source, lineno):
        self.source = source
        self.lineno = lineno
        self.locations = []

    def append(self, source, lineno, definition_type):
        if isinstance(lineno, int) and source!=None:
            self.locations.append(Location(source, lineno, definition_type))

    def remove(self, source, lineno):
        if isinstance(lineno, int) and source!=None:
            for location in self.locations:
                if location.source==source and location.lineno==lineno:
                    self.locations.remove(location)

    # def validate(self, source, lineno):
    #     return isinstance(lineno, int) and source!=None

    # returns source:lineno or <config>
    def get_source(self, config_file='<config>'):
        if self.type==ItemType.FROM_CONFIG:
            return config_file
        return '%s:%u' % (self._source, self._lineno)

    @property
    def source(self):
        if isinstance(self._lineno, ItemType):
            return None
        if SourceLocation.display_source==SourceType.FILENAME:
            return os.path.basename(self._source)
        return self._source

    @source.setter
    def source(self, source):
        if source==None:
            self._source = None
            return
        if not source:
            raise RuntimeError('source is an empty string')
        if SourceLocation.display_source==SourceType.REL_PATH:
            self._source = source
            return
        if SourceLocation.display_source==SourceType.REAL_PATH:
            self._source = os.path.realpath(source)
            return
        self._source = os.path.abspath(source)

    @property
    def full_source(self):
        if isinstance(self._lineno, ItemType):
            return None
        return self._source

    @property
    def lineno(self):
        if isinstance(self._lineno, ItemType):
            return 0
        return self._lineno

    @lineno.setter
    def lineno(self, lineno):
        if not isinstance(lineno, (int, ItemType)):
            raise RuntimeError('lineno not (int, ItemType): %s' % type(lineno))
        self._lineno = lineno

    @property
    def type(self):
        if isinstance(self._lineno, int):
            return ItemType.FROM_SOURCE
        return self._lineno

    @type.setter
    def type(self, value):
        if value==ItemType.FROM_SOURCE and not isinstance(self._lineno, int):
            raise RuntimeError('type=FROM_SOURCE not possible, use lineno=<int>')
        self.lineno = value

# stores translations with a list of languages
class i18n_lang(object):
    def __init__(self, lang, value):
        if isinstance(lang, str):
            lang = set(part.strip() for part in lang.split(';') if part and part.strip())
        if isinstance(lang, set):
            lang = list(lang)
        self.lang = lang
        self.value = value

    def has_lang(self, lang):
        return lang in self.lang

    def __repr__(self):
        return self.value

    def __str__(self):
        return '[%s]: "%s"' % (','.join(self.lang), self.value)

# stores all translations in a dictionary with the name as key
class i18n(object):
    def __init__(self, arg):
        self.arg = arg
        self.translations = {}

    @property
    def lang(self):
        return self.arg.lang

    @property
    def value(self):
        if self.lang==None:
            raise RuntimeError('language is None: %s:%u' % (self.arg.source, self.arg.lineno))
        return self.translations[self.lang]

    @value.setter
    def value(self, value):
        if self.lang==None:
            raise RuntimeError('language is None: %s:%u' % (self.arg.source, self.arg.lineno))
        item = i18n_lang(self.lang, value)
        for lang in item.lang:
            self.translations[lang] = item

    def get(self, languages_regex):
        for p_lang, lre in languages_regex.items():
            for lang, obj in self.items():
                if lre==DEFAULT_LANGUAGE:
                    return None
                elif lre.endswith(r'\Z'):
                    if re.match(lre, lang, re.I):
                        return (p_lang, lang, obj.value)
                elif lang.lower()==lre:
                    return (p_lang, lang, obj.value)
        return None

    def set(self, lang, value):
        item = i18n_lang(lang, value)
        for lang in item.lang:
            if lang in self.translations and value!=self.translations[lang].value:
                raise RuntimeError('cannot redefine value %s for %s: previous value %s' % (value, lang, self.translations[lang]))
            self.translations[lang] = item

    def cleanup(self):
        del self.arg

    def merge(self, merge_item):
        for lang, item in merge_item.items():
            if not lang in self.translations:
                self.translations[lang] = item
        merge_item.translations = self.translations

    def info(self):
        return self.__str__();

    def items(self):
        return self.translations.items()

    def values(self):
        return self.translations.values()

    def __repr__(self):
        return self.__str__(True)

    def __str__(self, repr=False):
        items = []
        for lang, item in self.items():
            if repr:
                items.append('%s: "%s"' % (lang, item.__repr__()))
            else:
                items.append(item.__str__())
        return ' '.join(items)

class Item(SourceLocation):

    DebugType = DebugType
    DEBUG = ITEM_DEBUG

    @property
    def DEFAULT_LANGUAGE(self):
        return DEFAULT_LANGUAGE

    # source/lineno             filename and line or None and ItemType
    # name                      name of the item
    # item                      used internally for the parser to verify that item is None
    # config_data               unmodified json data from the configuration file
    def __init__(self, definition_type=DefinitionType.DEFINE, source=None, lineno=None, name=None, item=None, config_data=None):
        SourceLocation.__init__(self, source, lineno)
        if item!=None:
            raise RuntimeError('item not None: %s' % item)
        if isinstance(definition_type, str):
            definition_type = DefinitionType(definition_type)
        if not isinstance(definition_type, DefinitionType):
            raise RuntimeError('invalid definition_type: %s' % definition_type)
        self.definition_type = definition_type
        SourceLocation.append(self, source, lineno, definition_type)
        self._static = definition_type==DefinitionType.DEFINE
        self._lang = self.DEFAULT_LANGUAGE
        self._value_buffer = None
        self.i18n = i18n(self)
        self._arg_num = 0
        self.name = name
        self._value = None
        self._auto = None
        self._config_data = config_data

    def __eq__(self, o: object) -> bool:
        return id(self) == id(o)

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    @property
    def has_value(self):
        return self._value!=None

    def get_value(self, lang_regex):
        value = self.i18n.get(lang_regex)
        if value!=None:
            return value
        return (self.DEFAULT_LANGUAGE, self.DEFAULT_LANGUAGE, self.value)

    @property
    def value(self):
        if self._auto!=None:
            return self._auto
        if self._value==None:
            return self.beautify(self.name)
        return self._value

    @property
    def has_auto_value(self):
        return self._auto!=None or self._value==None

    @property
    def auto_value(self):
        return self._auto

    @property
    def state(self):
        if isinstance(self._lineno, ItemType):
            return self._lineno
        if isinstance(self._lineno, int):
            return ItemType.FROM_SOURCE
        raise RuntimeError('invalid state')

    @property
    def arg_num(self):
        return self._arg_num

    @arg_num.setter
    def arg_num(self, num):
        self._arg_num = num
        if num>0 and self.name==None:
            raise RuntimeError('Name missing: %s' % (self))
        elif num>1 and self.definition_type in(DefinitionType.DEFINE, DefinitionType.AUTO_INIT) and self._value==None:
            raise RuntimeError('Value missing: %s' % (self))

    # get current language
    @property
    def lang(self):
        return self._lang

    # set current language
    @lang.setter
    def lang(self, lang):
        if lang==None:
            self._lang = None
            return
        self._lang = lang.strip()

    @property
    def i18n_values(self):
        values = self.i18n.values() # type: List[i18n_lang]
        return values

    # append to text buffer
    def append_value_buffer(self, value):
        if self.has_value_buffer:
            self._value_buffer += value
            return
        self._value_buffer = value

    def clear_value_buffer(self):
        self._value_buffer = None

    @property
    def has_value_buffer(self):
        return self._value_buffer!=None

    @property
    def value_buffer(self):
        if self.has_value_buffer:
            return self._value_buffer
        return ''

    def remove(self):
        SourceLocation.remove(self, self._source, self._lineno)
        self._source = None
        self._lineno = ItemType.REMOVED

    def push_value(self):
        if Item.DebugType.PUSH_VALUE in Item.DEBUG:
            print("push_value %u '%s'" % (self.arg_num, self._value_buffer))
        if self.arg_num==0:
            # first argument is the id
            self.name = self.value_buffer
        elif self.arg_num==1:
            # second argument is "default"
            if self.has_value_buffer:
                self._value = self.value_buffer
            else:
                self._value = None
        else:
            if self.arg_num % 2 == 0:
                if self.lang not in(None, self.DEFAULT_LANGUAGE):
                    raise RuntimeError('invalid language: %s' % (self))
                if not self.has_value_buffer:
                    raise RuntimeError('language is None: %s' % self)
                self.lang = self.value_buffer
            else:
                # set translation and remove language
                if not self.has_value_buffer:
                    raise RuntimeError('translation is None: %s' % self)
                self.i18n.value = self.value_buffer
                self.lang = None
        self.arg_num += 1
        self.clear_value_buffer()


    def beautify(self, name):
        name = name.replace('_', ' ')
        return name

    def validate(self):
        if self.name==None:
            raise RuntimeError('Name/id missing: %s' % (self))
        if self._value==None and self.definition_type in(DefinitionType.DEFINE, DefinitionType.AUTO_INIT):
            raise RuntimeError('Value missing: %s' % (self))

    def info(self, add_source=True):
        res = 'type=%s name=%s value=%s i18n=%s' % (self.definition_type, self.name, self._value, self.i18n.info())
        if add_source:
            if isinstance(self._lineno, int):
                res += ' source=%s:%u' % (self.source, self.lineno)
            else:
                res += ' source=%s' % self._lineno.value
        return res

    # cleanup object before storing
    def cleanup(self):
        del self._lang
        del self._value_buffer
        del self._arg_num
        self.i18n.cleanup()

    # returns True for
    #
    # item2=None:
    #   self is not item1 and item1.type is in types
    #
    # Item2!=None:
    #
    #   item1 is not item2 and item1.state is in states and item2.state is in types
    def is_type(self, item1, types=(ItemType.FROM_SOURCE, ItemType.FROM_CONFIG), item2=None):
        if item2==None:
            item2 = item1
            item1 = self
        if id(item1)==id(item2):
            return False
        return item1.type in types and item2.type in types

    def merge(self, item):
        self._merge_value(item)
        self._merge_auto_value(item)
        self._merge_type(item)
        self._merge_i18n(item)
        self._merge_item_locations(item)

    def _merge_value(self, item):
        if item._value!=None and self._value==None:
            self._value = item._value

    def _merge_auto_value(self, item):
        if item._auto!=None and self._value==None and self._auto==None:
            self._auto = item._auto
        # elif self._auto!=None and item._value==None and item._auto==None:
        #     item._auto = self._auto

    def _merge_type(self, item):
        if self._static or item._static:
            self._static = True
            item._static = True

    def _merge_i18n(self, item):
        self.i18n.merge(item.i18n)
        item.i18n = self.i18n

    def _merge_locations(locations, merge):
        if not isinstance(locations, list) or not isinstance(merge, list):
            raise RuntimeError('invalid type')
        # merge "merge" into "locations" and store sorted result in original "locations" list
        tmp = set(merge)|set(locations)
        locations.clear()
        locations.extend(sorted(tmp, key=lambda l: (l.source, l.lineno)))
        return locations

    def _merge_item_locations(self, item):
        if not self.is_type(item, (ItemType.FROM_SOURCE,)) or not item.has_locations:
            return
        item.locations = Item._merge_locations(self.locations, item.locations)

    @property
    def use_counter(self):
        return len([True for l in self.locations if l.definition_type==DefinitionType.SPGM])
        # n = 0
        # if self.locations:
        #     for location in self.locations:
        #         if location.definition_type==DefinitionType.SPGM:
        #             n += 1
        # return n

    # @property
    # def use_counter(self):
    #     return self._locations.use_counter

    # @property
    # def has_locations(self):
    #     return len(self._locations)

    @property
    def has_locations(self):
        return hasattr(self, 'locations') and len(self.locations)>0

    @property
    def locations_str(self):
        return self.get_locations_str()

    def get_locations_str(self, sep=', ', fmt='%s', locations=None):
        if locations==None:
            locations=self.locations
        if locations:
            return sep.join([l.format(fmt) for l in locations])
        return ''

    @property
    def static(self):
        return self._static

    def __str__(self):
        res = 'type=%s name=%s value="%s"' % (self.definition_type.value, self.name, self.value)
        if self.i18n.translations:
            res +=' i18n=%s' % self.i18n.__repr__()
        if self.has_auto_value:
            res += ' <auto_value>'
        res += ' use_counter=%u source=%s' % (self.use_counter, self.get_source())
        if self.has_locations:
            res += ' locations="%s"' % self.get_locations_str(sep=',')
        res += ' static=%s' % self.static

        if DebugType.ITEM_DEBUG_ATTR in (self.DEBUG) and hasattr(self, '_lang'):
            res +=  ' debug=%s' % {'lang': self.lang, 'args': self.arg_num, 'buffer': self._value_buffer, 'item_type': str(self.type)}
        return res
