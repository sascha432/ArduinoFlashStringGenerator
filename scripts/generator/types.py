#
# Author: sascha_lammers@gmx.de
#

import enum

class ExportType(enum.Enum):
    AUTO = 1,
    SOURCE = 2,
    CONFIG = 3,
    ALL = 4

class SubstListType(enum.Enum):
    STR = 'str'
    ABSPATH = 'abspath'
    PATTERN = 'pattern'

class SplitSepType(enum.Enum):
    NEWLINE = r'[\r\n]'
    WHITESPACE = r'\s'

class ItemType(enum.Enum):
    FROM_SOURCE = 0
    FROM_CONFIG = -1
    REMOVED = -2
    FROM_BUILD_DATABASE = -3

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

class FilterType(enum.Enum):
    NO_MATCH = 'NO_MATCH'
    INCLUDE = 'INCLUDE'
    EXCLUDE = 'EXCLUDE'

    def __str__(self):
        return str(self.value)

class SourceType(enum.Enum):
    REL_PATH = 'rel'
    ABS_PATH = 'abs'
    REAL_PATH = 'real'
    FILENAME = 'filename'

class DebugType(enum.Enum):
    TOKEN = 'token'
    PUSH_VALUE = 'push_value'
    DUMP_ITEMS = 'dump_items'
    EXCEPTION = 'exception'
    ITEM_DEBUG_ATTR = 'item_debug_attr'
    DUMP_READ_CONFIG = 'dump_read_config'
    DUMP_WRITE_CONFIG = 'dump_write_config'
    DUMP_MERGE_ITEMS = 'dump_merge_items'

