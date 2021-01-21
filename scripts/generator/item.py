#
# Author: sascha_lammers@gmx.de
#

# not in use
import copy

class i18n(object):
    def __init__(self):
        self.lang = None

class Item(object):
    def __init__(self, name=None, value='', file=None, line=0):
        self.name = name
        self.file = file
        self._line = line
        self.arg_num = 0
        self.value = value
        self.text = None
        self.default = None
        self.auto = None
        self.i18n = i18n()

    @property
    def line(self):
        return self._line

    @line.setter
    def line(self, value):
        if isinstance(value, int):
            self._line = value
            return
        self._line = int(value)

    def append_text(self, text):
        if self.text==None:
            self.text = text
            return
        self.text += text

    def compare_defaults(self, item):
        if self.default!=None and item.default!=None and self.default!=item.default:
            raise RuntimeError("Invalid redefinition of %s: %s:%u: '%s': previous definition: '%s'" % (item.name, item.file, item.line, item.default, self.default))
        if self.i18n.lang and item.i18n.lang and self.i18n.lang!=item.i18n.lang:
            raise RuntimeError("Invalid redefinition of %s: %s:%u: '%s': previous definition: '%s'" % (item.name, item.file, item.line, item.i18n.lang, self.i18n.lang))

    def merge(self, item):
        new_item = copy.deepcopy(self)
        new_item.default = item.default
        new_item.i18n = item.i18n
        new_item.auto = None
        return new_item

