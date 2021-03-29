#
# Author: sascha_lammers@gmx.de
#

from .types import DefinitionType, SourceType, ItemType
from os import path
import hashlib

class Location(object):
    def __init__(self, source, lineno, definition_type='REMOVED', column=None):
        self.source = source
        self.lineno = lineno
        self.column = column
        self.definition_type = DefinitionType(definition_type)

    def format(self, fmt):
        return fmt % ('%s:%s:%s (%s)' % (self.source, self.lineno, self.column, self.definition_type.value))

    def __eq__(self, o: object) -> bool:
        return id(self)==id(o) or (isinstance(self.lineno, int) and isinstance(o.lineno, int) and self.source==o.source and self.lineno==o.lineno and self.column==o.column)

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return str(tuple([self.source, str(self.lineno), str(self.column), str(self.definition_type.value)]))

    def __hash__(self):
        return hash('%s;%s;%s;%s' % (self.source, self.lineno, self.column, self.definition_type.value))

    # def _tolist(self):
    #     return [self.source, int(self.lineno), str(self.definition_type.value)]

class SourceLocation(object):

    display_source = SourceType.REL_PATH

    def __init__(self, source, lineno, column=None):
        self.source = source
        self.lineno = lineno
        self.column = column
        self._locations = []

    def append(self, source, lineno, definition_type, column):
        if isinstance(lineno, int) and source!=None:
            self._locations.append(Location(source, lineno, definition_type, column))

    def remove(self, source, lineno, column):
        if isinstance(lineno, int) and source!=None:
            for location in self._locations:
                if location.source==source and location.lineno==lineno and location.column==column:
                    self._locations.remove(location)

    # def validate(self, source, lineno):
    #     return isinstance(lineno, int) and source!=None

    # returns source:lineno or <config>
    def get_source(self, config_file='<config>'):
        if self.type==ItemType.FROM_CONFIG:
            return config_file
        return '%s:%u:%u' % (self._source, self._lineno, self.column)

    @property
    def source(self):
        if isinstance(self._lineno, ItemType):
            return None
        if SourceLocation.display_source==SourceType.FILENAME:
            return path.basename(self._source)
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
            self._source = path.realpath(source)
            return
        self._source = path.abspath(source)

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
    def source_hash(self):
        return hashlib.md5(self.source_str.encode()).digest().hex()

    @property
    def source_str(self):
        return '%s:%d:%u' % (self._source, self.lineno, self.column)

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

