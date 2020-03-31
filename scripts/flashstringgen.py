#
# Author: sascha_lammers@gmx.de
#

# pip install pcpp

import sys
import os
import argparse
import json
import time
import file_collector
import generator
from flash_string_preprocessor import FlashStringPreprocessor

parser = argparse.ArgumentParser(description="FlashString Generator")
parser.add_argument("-d", "--source-dir", help="Add all files in this directory", action='append', default=[])
parser.add_argument("-e", "--ext", help="Extensions to include", action='append', default=['.c', '.cpp', '.ino'])
parser.add_argument("-f", "--source-file", help="Add file", action='append', default=[])
parser.add_argument("-i", "--include-path", help="Add include path", action='append', default=[])
parser.add_argument("-I", "--src-filter-include", help="src_filter include", action='append', default=[])
parser.add_argument("-E", "--src-filter-exclude", help="src_filter exclude", action='append', default=[])
parser.add_argument("-w", "--workspace", help="PlatformIO workspace directory", default=None)
parser.add_argument("--output-declare", help="Header for automatically created strings", default="FlashStringGeneratorAuto.h")
parser.add_argument("--output-define", help="Source for automatically created strings", default="FlashStringGeneratorAuto.cpp")
parser.add_argument("--output-static", help="Source for statically created strings", default="FlashStringGeneratorAuto.static.txt")
parser.add_argument("--output-translate", help="Translation for name to value", default="FlashStringGeneratorAuto.json")
parser.add_argument("--include-file", help="File included in FlashStringGeneratorAuto.h/.cpp", default="FlashStringGenerator.h")
parser.add_argument("--database", help="Storage database file", default=".flashstringgen")
parser.add_argument("--output-dir", help="Directory for output files", default=".")
parser.add_argument("--force", help="Ignore modification time and file size", action="store_true", default=False)
parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)
parser.add_argument("-D", "--define", help="Define macro", action='append', default=[])
args = parser.parse_args()

def full_dir(dir, file):
    if dir!='':
        file = dir + os.sep + file
    return os.path.realpath(file)

args.verbose = True

# prepend output dir

args.output_declare = full_dir(args.output_dir, args.output_declare)
args.output_define = full_dir(args.output_dir, args.output_define)
args.output_static = full_dir(args.output_dir, args.output_static)
args.output_translate = full_dir(args.output_dir, args.output_translate)
args.database = full_dir(args.output_dir, args.database)

generator = generator.Generator()

# create a list of files to scan

fc = file_collector.FileCollector(args.database)
fc.read_database()
try:
    if len(args.source_dir)==0:
        parser.print_usage()
        print()
        raise RuntimeError('At least one --source_dir required')

    for filter in args.src_filter_include:
        fc.add_src_filter_include(filter, args.source_dir[0])
    for filter in args.src_filter_exclude:
        fc.add_src_filter_exclude(filter, args.source_dir[0])
    fc.add_src_filter_exclude(args.output_declare)
    fc.add_src_filter_exclude(args.output_define)
    fc.add_src_filter_exclude(args.output_static)
    fc.add_src_filter_exclude(args.output_translate)

    for file in args.source_file:
        fc.add_file(file)
    for dir in args.source_dir:
        fc.add_dir(dir, args.ext)
except OSError as e:
    print(e)
    sys.exit(1)
except RuntimeError as e:
    print(e)
    sys.exit(1)

files = fc.list()
if len(files) == 0:
    parser.print_usage()
    print()
    print("No source files found")
    sys.exit(1)

# create defines for the preprocessor

defines = []
for define in args.define:
    if '=' not in define:
        define = define + ' 1'
    else:
        list = define.split('=', 1)
        val = list[1]
        if len(val)>=4 and val.startswith('\\"') and val.endswith('\\"'):
            val = val[1:-2] + '"'
        define = list[0] + ' ' + val
    defines.append(define)

# read the translation file

generator.read_translate(args.output_translate)

if args.verbose:
    print("Extensions: " + str(args.ext))
    print("Modified: " + str(fc.modified()))
    print("Files: " + str(len(files)))
    print("Output declare: " + args.output_declare)
    print("Output define: " + args.output_define)
    print("Output static: " + args.output_static)
    print("Output translate: " + args.output_translate)
    print("Filter:")
    filters = fc.get_filter()
    for filter in filters['include']:
        print('+' + filter)
    for filter in filters['exclude']:
        print('-' + filter)
    print("Defines:")
    for define in defines:
        print(define)
    print("Includes:")
    for include in args.include_path:
        print(os.path.realpath(include))
    print("Files:")
    for file in files:
        print(file)
    print()
    print("Processing source files...")

# check if any source file was modified and scan the modified files

if fc.modified():
    fcpp = FlashStringPreprocessor()
    for define in defines:
        if args.verbose:
            print('define ' + define)
        fcpp.define(define)

    for include in args.include_path:
        fcpp.add_path(os.path.realpath(include))

    fcpp.add_ignore_include(args.output_declare)
    fcpp.add_ignore_include(args.output_define)
    fcpp.add_ignore_include(args.output_static)

    input = ''
    for file in files:
        # fcpp.add_path(os.path.dirname(file))
        if files[file]['state']!='-' and (args.force or files[file]['state']!=''):
            if args.verbose:
                print(file + ' ' + fc.long_state(files[file]))
            input = input + "#include \"" + file + "\"\n"
        else:
            if args.verbose:
                print("Skipping " + file + ' ' + fc.long_state(files[file]))

    fcpp.parse(input)
    # fcpp.write(sys.stdout)
    fcpp.find_strings()
    generator.append_used(fcpp.get_used())
    generator.append_defined(fcpp.get_defined())

    # create a list of strings that have been defined in the source code

    generator.update_statics()

    # create the auto generated files

    num = generator.write(args.output_declare, 'header', args.include_file)
    generator.write(args.output_define, 'define', args.include_file)
    generator.write(args.output_static, 'static')

    if args.verbose:
        used = generator.get_used()
        for string in used:
            item = used[string]
            if item['static']:
                type = 'static'
            else:
                type = 'auto'
            print(type + ' ' + item['name'] + '=' + generator.get_value(item))

    generator.write_translate(args.output_translate)
    fc.write_database()

    print(str(num) + " strings created")

else:
    print("No changes detected")
