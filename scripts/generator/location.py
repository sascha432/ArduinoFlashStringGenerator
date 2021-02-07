#
# Author: sascha_lammers@gmx.de
#

from .types import DefinitionType, SourceType, ItemType
from os import path

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
        return str(tuple([self.source, str(self.lineno), str(self.definition_type.value)]))

    def __hash__(self):
        return hash('%s;%s;%s' % (self.source, self.lineno, self.definition_type.value))

    def _tolist(self):
        return [self.source, int(self.lineno), str(self.definition_type.value)]

class SourceLocation(object):

    display_source = SourceType.REL_PATH

    def __init__(self, source, lineno):
        self.source = source
        self.lineno = lineno
        self._locations = []

    def append(self, source, lineno, definition_type):
        if isinstance(lineno, int) and source!=None:
            self._locations.append(Location(source, lineno, definition_type))

    def remove(self, source, lineno):
        if isinstance(lineno, int) and source!=None:
            for location in self._locations:
                if location.source==source and location.lineno==lineno:
                    self._locations.remove(location)

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
    def type(self):
        if isinstance(self._lineno, int):
            return ItemType.FROM_SOURCE
        return self._lineno

    @type.setter
    def type(self, value):
        if value==ItemType.FROM_SOURCE and not isinstance(self._lineno, int):
            raise RuntimeError('type=FROM_SOURCE not possible, use lineno=<int>')
        self.lineno = value

