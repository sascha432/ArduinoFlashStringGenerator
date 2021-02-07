#
# Author: sascha_lammers@gmx.de
#

import re

class i18n_config:
    DEFAULT_LANGUAGE = 'default'

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
                if lre==i18n_config.DEFAULT_LANGUAGE:
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
