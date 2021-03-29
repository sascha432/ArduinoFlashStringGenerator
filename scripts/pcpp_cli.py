#
# Author: sascha_lammers@gmx.de
#

import argparse
import json
import sys
import pickle
from os import path
try:
    from pcpp.preprocessor import Preprocessor, OutputDirective, Action
except Exception as e:
    print("-"*76)
    print("Cannot import pcpp")
    print("Exception: %s" % e)
    print("Path: %s" % sys.path)
    print()
    print("Run 'pio run -t spgm_install_requirements' to install the requirements")
    print()
    sys.exit(1)
from generator import SpgmPreprocessor

class LexToken(object):
    def __init__(self, tok):
        self.type = tok.type
        self.value = tok.value
        self.source = tok.source
        self.lineno = tok.lineno
        if hasattr(tok, 'expanded_from'):
            self.expanded_from = getattr(tok, 'expanded_from')

parser = argparse.ArgumentParser(description='PCPP')
parser.add_argument('--file', help="temporary file to exchange data", required=True, type=argparse.FileType('r+t'))
parser.add_argument('--cache', help="temporary file to cache the preprocessor object", type=argparse.FileType('r+b'))
parser.add_argument('-v', '--verbose', help='enable verbose output', action='store_true', default=False)
parser.add_argument('-i', '--info', help='display files being processed', action='store_true', default=False)
args = parser.parse_args()

def verbose(*vargs, **kwargs):
    if args.verbose:
        print(*vargs, **kwargs)

config = json.loads(args.file.read())

try:
    fcpp = SpgmPreprocessor(args.info)
    data = pickle.load(args.cache)
    fcpp.include_once = data['include_once']
    fcpp.macros = data['macros']
    verbose('cached macros: %u' % len(fcpp.macros))
except EOFError as e:
    fcpp = SpgmPreprocessor(args.info)
except Exception as e:
    verbose('failed to load object from cache: %s' % e)
    fcpp = SpgmPreprocessor(args.info)

for define, value in config['defines']:
    verbose('define %s=%s' % (define, value))
    fcpp.define('%s %s' % (define, value))

for define, value in config['pcpp_defines']:
    verbose('pcpp_defines %s=%s' % (define, value))
    fcpp.define('%s %s' % (define, value))

for include in config['include_dirs']:
    verbose('include_dir %s' % include)
    fcpp.add_path(include)

for skip_include in config['skip_includes']:
    verbose('skip_include %s' % skip_include)
    fcpp.add_skip_include(skip_include)

# print('source_excludes', True)
# for exclude_pattern in config.source_excludes:
#     print('exclude_pattern %s' % exclude_pattern)
#     fcpp.add_skip_include(exclude_pattern)

# verbose('target %s' % config['target'])

# combine all source files to speed up parsing
source = ''
for (absfile, file) in config['files']:
    verbose('files %s' % absfile)
    source += '#include "%s"\n' % absfile

verbose('preprocessing files %u files' % len(config['files']))
# parse files
fcpp.parse(source)
fcpp.find_strings()

items = []
for item in fcpp.items:
    for location in item.locations:
        item_out = {
            'source': item.source_str,
            'name': item.name,
            'type': str(location.definition_type),
            'value': item._value,
            'auto': item._value,
            'data': item._data
            # 'i18n': item.i18n.translations
        }
        items.append(item_out)

verbose('creating output files... %u items from %u files' % (len(items), len(fcpp.files)))

processed_files = sorted(fcpp.files)

out = {
    'files': processed_files,
    'items': items
}

# if args.verbose:
#     print(json.dumps(out, indent=2))

# store output in temporary file
args.file.seek(0)
args.file.truncate(0)
args.file.write(json.dumps(out))
args.file.close()

fcpp.cleanup()

args.cache.seek(0)
args.cache.truncate(0)

verbose('storing %u macros in cache' % (len(fcpp.macros)))

for key, macro in fcpp.macros.items():
    if macro.value!=None:
        for i, tok in enumerate(macro.value):
            macro.value[i] = LexToken(tok)
pickle.dump({
    'include_once': fcpp.include_once,
    'macros': fcpp.macros
}, args.cache)

sys.exit(0)