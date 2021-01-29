#
# Author: sascha_lammers@gmx.de
#

import json
import re
from typing import List, Dict
import sys

class BuildDatabase(object):

    def __init__(self, locations=None):
        self.find = self.get
        self.Location = getattr(sys.modules['generator.item'], 'Location')
        self.Item = getattr(sys.modules['generator.item'], 'Item')
        self._items = {} # type: Dict[str, List[self.Location]]
        if locations:
            self._fromjson(locations)

    def set(self, item):
        self._items[item.name] = item.locations

    def add(self, item):
        if item.name in self._items:
            self.Item._merge_locations(self._items[item.name], item.locations)
        else:
            self._items[item.name] = item.locations

    def get(self, name):
        if name in self._items:
            return self._items[name]
        return None

    def clear(self):
        self._items = {}

    def _fromjson(self, locations):
        for name, locations in locations.items():
            locations = [l for l in [self.Location(*location) for location in locations] if l.lineno>=0]
            self._items[name] = self.Item._merge_locations(name in self._items and self._items[name] or [], locations)

    def _tojson(self, indent=0):
        indent = ' '*indent
        keys = [item[0] for item in self._items.items() if item[1]]
        values = [list(map(lambda location: location._totuple(), locations)) for name, locations in self._items.items() if locations]
        return json.dumps(dict(zip(keys, values))).replace('{"', '{\n%s"' % indent).replace(']], "', ']],\n%s"' % indent).replace(']}', ']\n}')

    def __str__(self):
        return re.sub('((\[\[)|(\[)|\]\]|\])', lambda arg: (arg.group(1)=='[[' and '[(' or (arg.group(1)==']]' and ')]' or arg.group(1)=='[' and '(' or ')')), self._tojson().replace(']], "', ']],\n"')[2:-2])
