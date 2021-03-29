#
# Author: sascha_lammers@gmx.de
#

import argparse
import json
import sys
from os import path
import os
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

def get_hash(files):
    hash_files = []
    for file in files:
        rfile = path.realpath(file)
    st = os.stat(rfile)
    hash_files.append({rfile: '%u,%u' % (st.st_size, st.st_mtime)});
    hash_files.sort(reverse=False, key=lambda e: list(e)[0])
    return hash(json.dumps(hash_files))

parser = argparse.ArgumentParser(description='PCPP')
parser.add_argument('--file', help="temporary file to exchange data", required=True, type=argparse.FileType('r+t'))
parser.add_argument('-v', '--verbose', help='verbose', action='store_true', default=False)
args = parser.parse_args()

def verbose(*vargs, **kwargs):
    if args.verbose:
        print(*vargs, **kwargs)

config = json.loads(args.file.read())


# if config['target']['files']:
#     if get_hash(config['target']['files'])==config['target']['hash']:
#         print('no changes detected')
#         sys.exit(1)


fcpp = SpgmPreprocessor()
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
        }
        items.append(item_out)

verbose('creating output files... %u items from %u files' % (len(items), len(fcpp._files)))

processed_files = sorted(list(set(fcpp._files)), key=lambda val: val)

out = {
    'files': processed_files,
    'files_hash': get_hash(processed_files),
    'items': items
}

# if args.verbose:
#     print(json.dumps(out, indent=2))

# store output in temporary file
args.file.seek(0)
args.file.truncate(0)
args.file.write(json.dumps(out))

sys.exit(0)