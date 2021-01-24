#
# Author: sascha_lammers@gmx.de
#

import sys
from os import path
import argparse
import traceback
from generator import Item, DebugType, Generator, FileCollector, ModifiedType, FlashStringPreprocessor

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
parser.add_argument("--include-file", help="File included in FlashStringGeneratorAuto.h/.cpp", default="FlashStringGenerator.h")
parser.add_argument("--database", help="Storage database file", default=".flashstringgen")
parser.add_argument("--config", "--output-translate", help="Config file", default="FlashStringGeneratorAuto.json")
parser.add_argument("--output-dir", help="Directory for config and outout files", default=".")
parser.add_argument("--force", help="Force rebuild if no changes are detected", action="store_true", default=False)
parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)
parser.add_argument("-n", "--dry-run", help="Do not write any output files", action="store_true", default=False)
parser.add_argument("-D", "--define", help="Define macro", action='append', default=[])
parser.add_argument("-@", "--args-from-file", help="Read additional arguments from file, one argument per line", action=ArgfileAction, default=None)

args = parser.parse_args()

def verbose(msg):
    if args.verbose:
        print(msg)

# catch all
try:

    # second pass in case more have been read from file
    if args.args_from_file:
        args = parser.parse_args(sys.argv[1:] + args.args_from_file)

    if args.i18n:
        parser.error("--i18n: currently not supported yet")

    # args.verbose = True

    args.output_declare = FileCollector.prepend_dir(args.output_dir, args.output_declare)
    args.output_define = FileCollector.prepend_dir(args.output_dir, args.output_define)
    args.output_static = FileCollector.prepend_dir(args.output_dir, args.output_static)
    args.config = FileCollector.prepend_dir(args.output_dir, args.config)
    args.database = FileCollector.prepend_dir(args.output_dir, args.database)

    fc = FileCollector(args.database, args.config, args.verbose)

    generator = Generator()

    # read database and check for modifications
    fc.read_database()
    if not args.source_dir:
        parser.error('At least one --source_dir required');

    # add filters
    for filter in args.src_filter_include:
        fc.add_src_filter_include(filter, args.source_dir[0])
    for filter in args.src_filter_exclude:
        fc.add_src_filter_exclude(filter, args.source_dir[0])
    fc.add_src_filter_exclude(args.output_declare)
    fc.add_src_filter_exclude(args.output_define)
    fc.add_src_filter_exclude(args.output_static)
    fc.add_src_filter_exclude(args.config)

    # add source files
    for file in args.source_file:
        fc.add_file(file)
    for dir in args.source_dir:
        fc.add_dir(dir, args.ext)

    if not fc.files:
        raise RuntimeError('No source files found')

    fc.parse_defines(args.define)

    # read the translation file
    generator.read_config_json(fc.config_file)

    if args.verbose:
        print("Extensions: " + str(args.ext))
        print("Modified: " + str(fc.modified))
        print("Files: %u" % len(fc.files))
        print("Output declare: " + args.output_declare)
        print("Output define: " + args.output_define)
        print("Output static: " + args.output_static)
        print("Config file: " + args.config)
        print("Filter include/exclude: %u/%u" % (len(fc.filters['include']), len(fc.filters['exclude'])))
        print("Defines: %u" % len(fc.defines))
        print("Includes: %u" % len(args.include_path))
        print()

    verbose("Processing files...")

    # create preprocessor
    fcpp = FlashStringPreprocessor()
    for define, value in fc.defines.items():
        if args.verbose:
            print('define %s=%s' % (define, value))
        fcpp.define('%s %s' % (define, value))

    for include in args.include_path:
        fcpp.add_path(include)
        fc.add_include(include)

    fc.add_output_files(args.output_declare, args.output_define, args.output_static)

    fcpp.add_ignore_include(fc.output.declare)
    fcpp.add_ignore_include(fc.output.define)
    fcpp.add_ignore_include(fc.output.static)

    for exclude in fc.filters['exclude']:
        fcpp.add_ignore_include(exclude)

    if not args.force and not fc.modified:
        print('No changes detected')
        sys.exit(0)

    # add modified files
    input = ''
    for pathname, file in fc.files.items():
        if file.type!=ModifiedType.UNMODIFIED:
            input = input + "#include \"" + pathname + "\"\n"

        # if files[file]['state']!='-':  #and (args.force or files[file]['state']!=''):
        #     # if args.verbose:
        #     #     print(file + ' ' + fc.long_state(files[file]))
        #     input = input + "#include \"" + file + "\"\n"
        # else:
        #     if args.verbose:
        #         print("Skipping " + file + ' ' + fc.long_state(files[file]))

    # parse files
    fcpp.parse(input)
    fcpp.find_strings()

    generator.merge_items(fcpp.items)

    # create the auto generated files
    if args.dry_run:
        print("Dry run")
        num = 0
    else:
        # create output files
        num = generator.write(args.output_declare, 'header', args.include_file)
        generator.write(args.output_define, 'define', args.include_file)
        generator.write(args.output_static, 'static')

        # write config file and database
        generator.write_config_json(fc.config_file)
        fc.write_database()

    if args.verbose:
        for item in generator.items:
            print('%s %s=%s' % (item.type, item.name, item.value))

    print('%u strings created' % num)

except Exception as e:
    if Item.DebugType.EXCEPTION in Item.DEBUG or args.verbose:
        print(traceback.format_exc())
    else:
        print('Error: %s' % e)
        sys.exit(1)
