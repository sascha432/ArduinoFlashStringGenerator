#
# Author: sascha_lammers@gmx.de
#

import os
# import copy
# import enum
import re
from typing import List
# from typing import List, Tuple, Union
# from .config import SpgmConfig
from .types import DefinitionType, DebugType, ItemType
from .location import SourceLocation
from .i18n import i18n_config, i18n_lang, i18n

ITEM_DEBUG = frozenset([DebugType.EXCEPTION])

class Item(SourceLocation):

    DebugType = DebugType
    DEBUG = ITEM_DEBUG

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
        self._lang = i18n_config.DEFAULT_LANGUAGE
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
        return (i18n_config.DEFAULT_LANGUAGE, i18n_config.DEFAULT_LANGUAGE, self.value)

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
                if self.lang not in(None, i18n_config.DEFAULT_LANGUAGE):
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
        # print('merge %s, %s' % (self, item))
        self._merge_value(item)
        self._merge_auto_value(item)
        self._merge_i18n(item)
        self._merge_item_locations(item)

        if self._value!=None and self._auto!=None:
            raise RuntimeError('auto and value set: %s' % self)

        # print("result %s" % self)


    def _merge_value(self, item):
        if item._value!=None and item._auto!=None:
            raise RuntimeError('auto and value set: %s' % item)
        if item._value!=None and self._value==None:
            self._value = item._value
            self._auto = None

    def _merge_auto_value(self, item):
        if item._value!=None and item._auto!=None:
            raise RuntimeError('auto and value set: %s' % item)
        if item._auto!=None and self._value==None and self._auto==None:
            self._auto = item._auto

    def _merge_i18n(self, item):
        self.i18n.merge(item.i18n)
        item.i18n = self.i18n

    def _merge_locations(locations, merge, build=None):
        if not isinstance(locations, list) or not isinstance(merge, list):
            raise RuntimeError('invalid type')
        # merge "merge" into "locations" and store sorted result in original "locations" list
        tmp = set(merge)|set(locations)
        locations.clear()
        locations.extend(sorted(tmp, key=lambda l: (l.source, l.lineno)))
        return locations

    def _merge_build_locations(self, build):
        if self.use_counter==0 and not self.static:
            return
        locations = build.find(self.name)
        if locations:
            locations = Item._merge_locations(self._locations, locations).copy()

    def _merge_item_locations(self, item):
        if not self.is_type(item, (ItemType.FROM_SOURCE,)) or not item.has_locations:
            return
        Item._merge_locations(self._locations, item.locations)

    @property
    def use_counter(self):
        return len([True for l in self._locations if l.definition_type==DefinitionType.SPGM])

    @property
    def static(self):
        # l = [str(l) for l in self._locations if l.definition_type==DefinitionType.DEFINE]
        # if len(l)!=0:
        #     SpgmConfig.debug('static %s %s' % (self.name, l), True)
        #     return True
        # return False
        return len([True for l in self._locations if l.definition_type==DefinitionType.DEFINE])!=0

    @property
    def is_from_source(self):
        counter = self.use_counter
        if counter==0:
            return False
        return not self.static

    @property
    def has_locations(self):
        return hasattr(self, 'locations') and len(self.locations)>0

    @property
    def locations(self):
        return self._locations

    @locations.setter
    def locations(self, locations):
        self._locations = locations

    @property
    def locations_str(self):
        return self.get_locations_str()

    def get_locations_str(self, sep=', ', fmt='%s', locations=None):
        if locations==None:
            locations=self.locations
        if locations:
            return sep.join([l.format(fmt) for l in locations])
        return ''

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
            res +=  ' debug=%s' % {'lang': self.lang, 'args': self.arg_num, 'buffer': self._value_buffer, 'item_type': str(self.type).split('.')[-1], '_auto': self._auto, '_value': self._value}
        return res
