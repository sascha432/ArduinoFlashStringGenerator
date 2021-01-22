
#
# Author: sascha_lammers@gmx.de
#

import os
import copy
import enum

class Location(object):
    def __init__(self, source, lineno):
        self.source = source
        self.lineno = lineno

    def __eq__(self, o: object) -> bool:
        return id(self)==id(o) or (self.lineno>=0 and o.lineno>=0 and self.source==o.source and self.lineno==o.lineno)

    def __str__(self):
        return '%s:%u' % (self.source, self.lineno)

    def __repr__(self):
        return '<%s %s:%u at %X>' % (self.__class__.__qualname__, self.source, self.lineno, int(id(self)))

class SourceType(enum.Enum):
    REL_PATH = 'rel'
    ABS_PATH = 'abs'
    REAL_PATH = 'real'
    FILENAME = 'filename'

class SourceLocation(object):

    display_source = SourceType.REL_PATH

    def __init__(self, source, lineno):
        self.source = source
        self._lineno = int(lineno)
        self._use_counter = Counter()
        self.locations = [Location(self.source, self.lineno)]

    @property
    def source(self):
        if SourceLocation.display_source==SourceType.FILENAME:
            return os.path.basename(self._source)
        return self._source

    @source.setter
    def source(self, source):
        if SourceLocation.display_source==SourceType.REL_PATH:
            self._source = source
        elif SourceLocation.display_source==SourceType.REAL_PATH:
            self._source = os.path.realpath(source)
        else:
            self._source = os.path.abspath(source)

    @property
    def full_source(self):
        return self._source

    @property
    def lineno(self):
        return self._lineno

    @lineno.setter
    def lineno(self, lineno):
        if not isinstance(lineno, int):
            raise RuntimeError('lineno not int: %s' % type(lineno))
            self._lineno = int(lineno)
            return
        self._lineno = lineno

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
        return '[%s]: %s' % (','.join(self.lang), self.value)

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

    # get raises an exception if lang does not exist
    def get(self, lang):
        return self.translations[lang]

    # find returns None if the lang does not exist
    def find(self, lang):
        if lang in self.translations:
            print('find',lang,self.get(lang))
            return (lang, self.get(lang))
        print('find = None',lang)
        return (None, None)

    def set(self, lang, value):
        item = i18n_lang(lang, value)
        for lang in item.lang:
            if lang in self.translations and value!=self.translations[lang]:
                raise RuntimeError('cannot redefine value %s for %s: previous value %s' % (value, lang, self.translations[lang]))
            self.translations[lang] = item

    def cleanup(self):
        del self.arg
        # self.translations = self._create_new_list()

    def merge(self, merge_item):
        for lang, item in merge_item.translations.items():
            if not lang in self.translations:
                self.translations[lang] = item
        merge_item.translations = self.translations

    def info(self):
        return self.__str__();

    def items(self):
        return self.translations.items()

    def __repr__(self):
        return self.__str__(True)

    def __str__(self, repr=False):
        items = []
        for lang, item in self.items():
            if repr:
                items.append('%s: %s' % (lang, item.__repr__()))
            else:
                items.append(item.__str__())
        return ' '.join(items)

class Counter(object):
    def __init__(self, value=0):
        self._counter = value

    def __eq__(self, o: object) -> bool:
        return id(self) == id(o)

    @property
    def counter(self):
        return self._counter

    @counter.setter
    def counter(self, value):
        self._counter = value

class ItemType(enum.Enum):
    DEFINE = 'DEFINE'
    SPGM = 'SPGM'
    AUTO_INIT = 'AUTO_INIT'

class DebugType(enum.Enum):
    TOKEN = 'token'
    PUSH_VALUE = 'push_value'
    DUMP_ITEMS = 'dump_items'
    EXCEPTION = 'exception'

class Item(SourceLocation):

    ItemType = ItemType

    DebugType = DebugType
    DEBUG = frozenset([DebugType.DUMP_ITEMS, DebugType.EXCEPTION])

    DEFAULT_LANGUAGE = 'default'

    def __init__(self, item=None, type=ItemType.DEFINE, source=None, lineno=-1, name=None):
        SourceLocation.__init__(self, source, lineno)
        if item!=None:
            raise RuntimeError('item not None: %s' % item)
        if isinstance(type, str):
            type = ItemType(type)
        if not type in(ItemType.DEFINE, ItemType.SPGM, ItemType.AUTO_INIT):
            raise RuntimeError('invalid type: %s' % type)
        self.type = type
        self._lang = self.DEFAULT_LANGUAGE
        self._value_buffer = None
        self.i18n = i18n(self)
        self._arg_num = 0
        self.name = name
        self._value = None
        self.auto = False
        self.unused = lineno==-1
        self._static = type in(ItemType.DEFINE, ItemType.AUTO_INIT)

    def __eq__(self, o: object) -> bool:
        return id(self) == id(o)

    @property
    def removed(self):
        return self.lineno==-2

    def remove(self):
        self.name + '$$$REMOVED$$$ ' + self.name
        self.lineno = -2

    @property
    def has_value(self):
        return self._value!=None

    @property
    def value(self):
        if self._value==None:
            return self.beautify(self.name)
        return self._value

    @property
    def is_valid(self):
        return self._lineno>=0

    @property
    def is_invalid(self):
        return self._lineno<0

    @property
    def from_config_file(self):
        return self.lineno==-1 and self.source==None

    @property
    def arg_num(self):
        return self._arg_num

    @arg_num.setter
    def arg_num(self, num):
        self._arg_num = num
        if num>0 and self.name==None:
            raise RuntimeError('Name missing: %s' % (self))
        elif num>1 and self.type in(ItemType.DEFINE, ItemType.AUTO_INIT) and self._value==None:
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
                if self.lang not in(None, Item.DEFAULT_LANGUAGE):
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
        if self._value==None and self.type in(ItemType.DEFINE, ItemType.AUTO_INIT):
            raise RuntimeError('Value missing: %s' % (self))

    def info(self, add_source=True):
        res = 'type=%s name=%s value=%s i18n=%s' % (self.type, self.name, self._value, self.i18n.info())
        if add_source:
            res += ' source=%s:%u' % (self.source, self.lineno)
        return res

    # cleanup object before storing
    def cleanup(self):
        del self._lang
        del self._value_buffer
        del self._arg_num
        self.i18n.cleanup()

    def merge(self, merge_item):
        if merge_item._value!=None and self._value==None:
            self._value = merge_item._value
        if merge_item._static:
            self._static = True
        if self._static:
            merge_item._static = True
        # merge translations and keep single copy
        self.i18n.merge(merge_item.i18n)
        merge_item.i18n = self.i18n

    # add counters and replace both with the same object
    def copy_counter(self, item):
        if not hasattr(self, '_use_counter') or not hasattr(item, '_use_counter') or id(self._use_counter)==id(item._use_counter):
            return
        self._use_counter.counter += item._use_counter.counter
        item._use_counter = self._use_counter

    # add locations from item, remove duplicates and store the same object in both items
    def copy_locations(self, item):
        if self.is_invalid or item.is_invalid or \
            not item.has_locations or not self.has_locations or \
            id(self.locations)==id(item.locations):
            return
        tmp = []
        # tmp.extend(self.locations)
        for item2 in self.locations:
            tmp.append(item2)
        for item2 in item.locations:
            if item!=item2:
                # if not item2 in self.locations:
                print('COPY APPEND',item2.__repr__(),item.__repr__())
                tmp.append(item2)
        if len(tmp)==0:
            return
        # tmp.extend(item.locations)
        # tmp = set(tmp)
        self.locations.clear()
        self.locations.extend(tmp)
        # for item in tmp:
        #     self.locations.append(tmp)
        item.locations = self.locations

    @property
    def has_use_counter(self):
        return hasattr(self, '_use_counter')

    @property
    def use_counter(self):
        return self._use_counter.counter

    @use_counter.setter
    def use_counter(self, value):
        self._use_counter.counter = value
        # if isinstance(type(value), Counter):
        #     if id(value)!=id(self._use_counter):
        #         value.counter += self._use_counter.counter
        #         self._use_counter = value
        # else:
        #     self._use_counter.counter += value

    @property
    def has_locations(self):
        return hasattr(self, 'locations')

    @property
    def locations_str(self):
        return self.get_locations_str()

    @property
    def static(self):
        return self._static

    def get_locations_str(self, sep=', ', fmt='%s'):
        if not self.has_locations or not self.locations:
            return ''
        return sep.join([(fmt % l) for l in self.locations])

    def __str__(self):
        res = 'type=%s name=%s value=%s' % (self.type._value_, self.name, self.value)
        if self.i18n.translations:
            res +=' i18n=%s' % self.i18n.__repr__()
        res += ' source=%s:%u' % (self.source, self.lineno)
        if hasattr(self, 'auto') or not self.has_value:
            res += ' auto=True'
        if self.has_use_counter:
            res += ' use_counter=%u' % self.use_counter
        if self.has_locations:
            res += ' locations=%s' % self.get_locations_str(sep=',')
        if hasattr(self, '_lang'):
            res +=  ' debug=%s' % {'lang': self.lang, 'args': self.arg_num, 'buffer': self._value_buffer}
        res += ' static=%s' % self._static
        return res
