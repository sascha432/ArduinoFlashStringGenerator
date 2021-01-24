#
# Author: sascha_lammers@gmx.de
#

import sys
import os
from os import path
import argparse
import json
import time
import traceback
from generator import Item, DebugType, Generator, FileCollector, FlashStringPreprocessor

class ArgfileAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        extra_args = []
        try:
            with open(values, "rt") as file:
                for line in file:
                    extra_args.append(line.rstrip('\r\n'));
        except Exception as e:
            raise argparse.ArgumentError(self, 'cannot read: %s: %s' % (e, values))
        if extra_args:
            setattr(namespace, self.dest, extra_args)

parser = argparse.ArgumentParser(description="FlashString Generator 0.0.3")
parser.add_argument("-p", "--project_dir", help="PlatformIO project directory", default=None, required=True)
parser.add_argument("-d", "--source-dir", help="Add all files in these directories applying src_filter", action='append', default=[])
parser.add_argument("-e", "--ext", help="Extensions to include", action='append', default=['.c', '.cpp', '.ino'])
parser.add_argument("-f", "--source-file", help="Add file", action='append', default=[])
parser.add_argument("-i", "--include-path", help="Add include path", action='append', default=[])
parser.add_argument("-I", "--src-filter-include", help="src_filter include", action='append', default=[])
parser.add_argument("-E", "--src-filter-exclude", help="src_filter exclude", action='append', default=[])
parser.add_argument("--i18n", help="Select language to use", default=None)
parser.add_argument("--output-declare", help="Header for automatically created strings", default="FlashStringGeneratorAuto.h")
parser.add_argument("--output-define", help="Source for automatically created strings", default="FlashStringGeneratorAuto.cpp")
parser.add_argument("--output-static", help="Source for statically created strings", default="FlashStringGeneratorAuto.static.txt")
parser.add_argument("--output-translate", help="Translation for name to value", default="FlashStringGeneratorAuto.json")
parser.add_argument("--include-file", help="File included in FlashStringGeneratorAuto.h/.cpp", default="FlashStringGenerator.h")
parser.add_argument("--database", help="Storage database file", default=".flashstringgen")
parser.add_argument("--output-dir", help="Directory for output files", default=".")
parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)
parser.add_argument("-n", "--dry-run", help="Do not write any output files", action="store_true", default=False)
parser.add_argument("-D", "--define", help="Define macro", action='append', default=[])
parser.add_argument("-@", "--args-from-file", help="Read additional arguments from file, one argument per line", action=ArgfileAction, default=None)

args = parser.parse_args()

try:
    # second pass in case more have been read from file
    if args.args_from_file:
        args = parser.parse_args(sys.argv[1:] + args.args_from_file)

    if args.i18n:
        parser.error("--i18n: currently not supported")

    def verbose(msg):
        if args.verbose:
            print(msg)

    def full_dir(dir, file):
        if dir!='':
            file = dir + os.sep + file
        return path.realpath(file)

    # args.verbose = True

    # prepend output dir

    args.output_declare = full_dir(args.output_dir, args.output_declare)
    args.output_define = full_dir(args.output_dir, args.output_define)
    args.output_static = full_dir(args.output_dir, args.output_static)
    args.output_translate = full_dir(args.output_dir, args.output_translate)
    args.database = full_dir(args.output_dir, args.database)

    generator = Generator()

    # create a list of files to scan

    fc = FileCollector(args.database)
    fc.read_database()
    try:
        if len(args.source_dir)==0:
            parser.error('At least one --source_dir required');

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
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    files = fc.list()
    if len(files) == 0:
        parser.error("No source files found")

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

    generator.read_config_json(args.output_translate)

    if args.verbose:
        print("Extensions: " + str(args.ext))
        print("Modified: " + str(fc.modified()))
        print("Files: " + str(len(files)))
        print("Output declare: " + args.output_declare)
        print("Output define: " + args.output_define)
        print("Output static: " + args.output_static)
        print("Output translate: " + args.output_translate)
        filters = fc.get_filter()
        print("Filter include/exclude: %u/%u" % (len(filters['include']), len(filters['exclude'])))
        print("Defines: %u" % len(defines))
        print("Includes: %u" % len(args.include_path))
        print("Files: %u" % len(files))
        print()

    verbose("Processing files...")

    # check if any source file was modified and scan the modified files

    if fc.modified():
        fcpp = FlashStringPreprocessor()
        for define in defines:
            # if args.verbose:
            #     print('define ' + define)
            fcpp.define(define)

        for include in args.include_path:
            fcpp.add_path(path.realpath(include))

        fcpp.add_ignore_include(args.output_declare)
        fcpp.add_ignore_include(args.output_define)
        fcpp.add_ignore_include(args.output_static)

        filters = fc.get_filter()
        for exclude in filters['exclude']:
            fcpp.add_ignore_include(exclude)

        input = ''
        for file in files:
            if files[file]['state']!='-':  #and (args.force or files[file]['state']!=''):
                # if args.verbose:
                #     print(file + ' ' + fc.long_state(files[file]))
                input = input + "#include \"" + file + "\"\n"
            # else:
            #     if args.verbose:
            #         print("Skipping " + file + ' ' + fc.long_state(files[file]))

        fcpp.parse(input)

        fcpp.find_strings()

        generator.merge_items(fcpp.items)

        if DebugType.DUMP_ITEMS in Item.DEBUG:
            print('merged items:')
            generator.dump_merged()
            print('-'*76)

        # create the auto generated files
        if args.dry_run:
            print("Dry run")
            num = 0;
        else:
            num = generator.write(args.output_declare, 'header', args.include_file)
            generator.write(args.output_define, 'define', args.include_file)
            generator.write(args.output_static, 'static')

            generator.write_config_json(args.output_translate)
            fc.write_database()

        if args.verbose:
            for item in generator.items:
                if item.static:
                    type = 'static'
                elif item.has_auto_value:
                    type = 'auto'
                else:
                    type = 'default'
                print('%s %s=%s' % (type, item.name, item.value))

        print('%u strings created' % num)

    else:
        print("No changes detected")

except Exception as e:
    if Item.DebugType.EXCEPTION in Item.DEBUG or args.verbose:
        print(traceback.format_exc())
    else:
        print('Error: %s' % e)
        sys.exit(1)
