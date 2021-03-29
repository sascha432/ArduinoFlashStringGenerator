#
# Author: sascha_lammers@gmx.de
#

class SpgmCache(object):

    _cache = {}

    def __init__(self, env):
        self._env = env

    def __cache(name, lazy_load):
        if not name in SpgmCache._cache:
            SpgmCache._cache[name] = lazy_load()
        return SpgmCache._cache[name]

    def _cache_item_name(self, name):
        return 'env_%s_item_%s' % (id(self._env), name)

    def cache(self, name, lazy_load):
        return SpgmCache.__cache(self._cache_item_name(name), lazy_load)

    def is_cached(self, name):
        return self._cache_item_name(name) in SpgmCache._cache

    def get_cache(self, name):
        name = self._cache_item_name(name)
        if not name in SpgmCache._cache:
            return None
        return SpgmCache._cache[name]

    def set_cache(self, name, value):
        name = self._cache_item_name(name)
        SpgmCache._cache[name] = value
