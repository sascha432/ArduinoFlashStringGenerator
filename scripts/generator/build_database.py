#
# Author: sascha_lammers@gmx.de
#

import json
from typing import List, Dict
from .location import Location
from .item import Item

class BuildDatabase(object):

    def __init__(self, locations=None):
        self.find = self.get
        self._items = {} # type: Dict[str, List[Location]]
        if locations:
            self._fromjson(locations)

    def set(self, item):
        self._items[item.name] = item.locations

    def add(self, item):
        if item.name in self._items:
            Item._merge_locations(self._items[item.name], item.locations)
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
            locations = [l for l in [Location(*location) for location in locations] if l.lineno>=0]
            self._items[name] = Item._merge_locations(name in self._items and self._items[name] or [], locations)

    def _tojson(self, indent=None):
        return json.dumps( \
            { name: list(map(lambda location: location._tolist(), locations)) for name, locations in self._items.items() if locations }, \
            indent=indent, sort_keys=True \
        )

    def __str__(self):
        return self._tojson(indent=4)
