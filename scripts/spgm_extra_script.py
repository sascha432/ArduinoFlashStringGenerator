
#
# Author: sascha_lammers@gmx.de
#

from SCons.Script import ARGUMENTS
from SCons.Node import FS
from SCons.Script.SConscript import SConsEnvironment
from SCons.Script.SConscript import DefaultEnvironmentCall
from SCons.Node import FS
import os
from os import path
import sys
import inspect
import tempfile
import shlex
import subprocess
import fnmatch
from generator import FilterType, Generator, SpgmConfig, Item, ItemType
from generator import SpgmPreprocessor
import threading
import generator
from typing import List
from pathlib import Path
import enum
import time

env = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("env")

class ExportType(enum.Enum):
    AUTO = 1,
    SOURCE = 2,
    CONFIG = 3,
    ALL = 4

class SpgmExtraScript(object):

    def __init__(self):
        self.verbose = SpgmConfig._verbose
        # self.env = env
        # self.projenv = projenv
        # self.libs = {}
        self.source_files = []
        # self.project_src_dir = path.abspath(env.subst('$PROJECT_SRC_DIR'))
        # self.project_dir = path.abspath(env.subst('$PROJECT_DIR'))
        self.lock = threading.Lock()
        self.log_file = None

    def _touch_output_files(env):
        config = SpgmConfig(env)

        # append empty line to force recompilation
        # with open(config.declaration_file, 'at') as file:
        #     file.write('\n')
        with open(config.definition_file, 'at') as file:
            file.write('\n')

        # Path(config.declaration_file).touch()
        # Path(config.definition_file).touch()

    # def _get_lib(self, lib_name):
    #     if lib_name in self.libs:
    #         return self.libs[lib_name]
    #     return None

    # def create_libs(self, env, projenv):
    #     self.libs = {
    #         None: self._create_lib(None, env, projenv)
    #     }
    #     for lib in self.projenv.GetLibBuilders():
    #         lib = self._create_lib(lib.name, env, projenv, lib)
    #         if lib:
    #             self.libs[lib._name] = lib

    # def _create_lib(self, lib_name, env, projenv, lib=None):
    #     return LibContainer(lib_name, env, projenv, lib)

    # def _get_script_location(self):
    #     return path.abspath(path.join(path.dirname((inspect.getfile(inspect.currentframe()))), 'spgm_generator.py'))

    def build_spgm_lib(self, lib_name, env, lib_org=None):

        # print(env.get("PIOBUILDFILES"))
        # print(dir(env))
        print(env.Dump())
        sys.exit(0)

        if not self.libs:
            if self.verbose:
                print("Creating libraries...")
            self.create_libs(self.env, self.projenv)

        if self.verbose:
            print('-'*76)
            if lib_name:
                print('Library: %s' % lib_name)
            else:
                print('Project')
            print('-'*76)

        lib = self._get_lib(lib_name)
        if lib==None:
            raise RuntimeError('%s not found' % lib_name)
        env = lib.env

        sources = lib.get_sources(lib.src_filter, lib.src_dir, self.source_files)
        if not sources:
            if self.verbose:
                print('No source files, skipping %s' % lib.name)
            return

        args_file = tempfile.NamedTemporaryFile('w+t', delete=False)

        args = [
            env.subst("$PYTHONEXE"),
            self._get_script_location(),
            '--src-dir=%s' % lib.src_dir,
            '--project-dir=%s' % self.project_dir,
            '-@', args_file.name
        ]
        # if force:
        #     args.append('--force')
        if self.verbose:
            args.append('--verbose')

        for define in lib.cpp_defines:
            args_file.write('--define=%s=%s\n' % (define[0], str(define[1])));
            # args_file.write('--define=%s=%s\n' % (define[0], env.subst(str(define[1]))));

        args_file.write('--define=__cplusplus=201103L\n');

        mmcu = env.subst("$BOARD_MCU").lower()
        if mmcu=="esp8266":
            args_file.write('--define=ESP8266=1\n');
        elif mmcu=="esp32":
            args_file.write('--define=ESP32=1\n');
        elif mmcu=="atmega328p":
            args_file.write('--define=__AVR__=1\n');
            args_file.write('--define=__AVR_ATmega328P=1\n');
        elif mmcu=="atmega328pb":
            args_file.write('--define=__AVR__=1\n');
            args_file.write('--define=__AVR_ATmega328PB=1\n');
        elif mmcu=="atmega48p":
            args_file.write('--define=__AVR__=1\n');
            args_file.write('--define=__AVR_ATmega48P=1\n');
        elif mmcu=="atmega88p":
            args_file.write('--define=__AVR__=1\n');
            args_file.write('--define=__AVR_ATmega88P=1\n');
        elif mmcu=="atmega168p":
            args_file.write('--define=__AVR__=1\n');
            args_file.write('--define=__AVR_ATmega168P=1\n');
        else:
            print("WARNING: -mmcu=%s not supported. Some defines might be missing. Check https://gcc.gnu.org/onlinedocs/gcc/AVR-Options.html for a full list" % mmcu);

        for src in sources:
            args_file.write('--source=%s\n' % src)

        for include_dir in lib.include_dirs:
            args_file.write('--include-dir=%s\n' % include_dir)

        for arg in lib.extra_args:
            args_file.write(arg);
            args_file.write('\n')

        args.append('2>&1')

        if self.verbose:
            parts = []
            for arg in args:
                parts.append(shlex.quote(arg))
            parts[0] = args[0]
            print(' '.join(parts))

        args_file.close();

        if self.verbose:
            with open(args_file.name, 'rt') as f:
                print('arguments file %s:' % args_file.name)
                n = 0
                for line in (line.strip() for line in f.readlines() if line.strip()):
                    print(line)
                print('<EOF>')

        try:
            popen = subprocess.run(args, shell=True)
        except Exception as e:
            raise e
        finally:
            os.unlink(args_file.name);

        return_code = popen.returncode
        if return_code!=0:
            print('%s failed to run: %s' % (path.basename(self._get_script_location()), str(return_code)))
            sys.exit(return_code)


    def run_build_spgm(self, target, source, env):
        print('%sBUILDSPGM%s' % ('-'*20,'-'*20))
        for lib in self.projenv.GetLibBuilders():
            self.build_spgm_lib(lib.name, lib.env, lib)
        self.build_spgm_lib(None, env)

    def export_database(self, config, type):
        gen = Generator(config, [])
        gen.language = config.output_language
        gen.read_json_database(config.json_database, config.json_build_database)

        gen.merge_items(None)

        print('FLASH_STRING_GENERATOR_AUTO_INIT(')

        def escape(s):
            return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')

        for item in sorted(gen._merged.values(), key=lambda item: item.name):
            if (\
                    type==ExportType.AUTO and item.has_auto_value \
                ) or ( \
                    type==ExportType.SOURCE and item.type==ItemType.FROM_SOURCE \
                ) or ( \
                    type==ExportType.CONFIG and item.type==ItemType.FROM_CONFIG \
                ) or ( \
                    type==ExportType.ALL \
                ):
                parts = [item.name, escape(item.value)]

                item = item # type: Item
                trans = item.i18n.values()
                if trans:
                    for lang in trans:
                        parts.append('%s: %s' % (','.join(lang.lang), escape(lang.value)))

                print('    // %s' % item.get_locations_str())
                print('    AUTO_STRING_DEF(%s)' % ', '.join(parts))

        print(');')

    def run_export_config(self, target, source, env):
        self.export_database(SpgmConfig(env), ExportType.CONFIG)

    def run_export_all(self, target, source, env):
        self.export_database(SpgmConfig(env), ExportType.ALL)

    def run_export_auto(self, target, source, env):
        self.export_database(SpgmConfig(env), ExportType.AUTO)


    def run_install_requirements(self, source, target, env):
        env.Execute("$PYTHONEXE -m pip install pcpp==1.22")


    def run_spgm_generator(self, target, source, env):


        start_time = time.monotonic()

        config = SpgmConfig(env)

        if self.log_file==None:
            SpgmConfig.debug('creating log file %s' %config.log_file, True)
            self.log_file = open(config.log_file, 'at')

            self.log_file.write('--- source files:\n')
            for node in self.source_files:
                self.log_file.write('%s -> %s\n' % (node.get_abspath(), node.srcnode().get_abspath()))


        SpgmConfig.debug('source files', True)
        files = [] # type: List[FS.File]
        for file in source:
            include = True
            file = file.get_abspath()
            if file==config.definition_file:
                continue
            for exclude in config.source_excludes:
                # SpgmConfig.debug('fnmatch (%s, %s) = %s' % (file, exclude, fnmatch.fnmatch(file, exclude)))
                if fnmatch.fnmatch(file, exclude):
                    include = False
                    break
            if include:
                SpgmConfig.debug('source %s' % file)
                files.append(file)

        if not files:
            SpgmConfig.debug('no files for %s' % target)
            return

        SpgmConfig.verbose('waiting for lock...')
        if not self.lock.acquire(True, 900.0):
            raise RuntimeError('cannot aquire lock for run_spgm_generator. target=%s' % target)
        try:
            SpgmConfig.verbose('lock acquired...')
            # if config.is_cached('generator') and False:
                # SpgmConfig.debug('loading generator from cache', True)
                # gen = config.get_cache('generator')
            # else:
            if True:
                SpgmConfig.debug('creating generator object', True)
                gen = Generator(config, files)
                gen.language = config.output_language
                gen.read_json_database(config.json_database, config.json_build_database)
                # config.set_cache('generator', gen)

            if config.is_cached('fcpp'):
                SpgmConfig.debug('loading preprocessor from cache', True)
                fcpp = config.get_cache('fcpp')
            else:
                SpgmConfig.debug('creating preprocessor object', True)
                SpgmConfig.debug('defines', True)
                fcpp = SpgmPreprocessor()
                for define, value in config.defines:
                    SpgmConfig.debug('define %s=%s' % (define, value))
                    fcpp.define('%s %s' % (define, value))

                for define, value in config.pcpp_defines:
                    SpgmConfig.debug('pcpp_defines %s=%s' % (define, value))
                    fcpp.define('%s %s' % (define, value))

                SpgmConfig.debug('include_dirs', True)
                for include in config.include_dirs:
                    SpgmConfig.debug('include_dir %s' % include)
                    fcpp.add_path(include)

                SpgmConfig.debug('skip_includes', True)
                for skip_include in config.skip_includes:
                    SpgmConfig.debug('skip_include %s' % skip_include)
                    fcpp.add_skip_include(skip_include)

                # SpgmConfig.debug('source_excludes', True)
                # for exclude_pattern in config.source_excludes:
                #     SpgmConfig.debug('exclude_pattern %s' % exclude_pattern)
                #     fcpp.add_skip_include(exclude_pattern)

                config.set_cache('fcpp', fcpp)

            SpgmConfig.debug('files', True)
            parts = []
            for file in gen.files:
                SpgmConfig.debug('file %s' % file)
                parts.append('#include "%s"' % file)

            self.log_file.write('--- preprocessing files:\n')
            for file in gen.files:
                self.log_file.write('%s\n' % file)

            SpgmConfig.debug('preprocessing files', True)
            # parse files
            fcpp.parse('\n'.join(parts))
            fcpp.find_strings()

            SpgmConfig.debug('creating output files', True)
            gen.merge_items(fcpp.items)

            num = len(fcpp.items)
            include_counter = fcpp.include_counter

            self.log_file.write('--- result: %u items, %u include files, time %.3f seconds\n' % (num, include_counter, time.monotonic() - start_time))
            for item in fcpp.items:
                self.log_file.write('%s\n' % item)

            fcpp.cleanup()

            SpgmConfig.debug('output_language %s' % gen.language)
            SpgmConfig.debug('declaration_file %s' % config.declaration_file)
            SpgmConfig.debug('definition_file %s' % config.definition_file)
            SpgmConfig.debug('declaration_include_file %s' % config.declaration_include_file)
            SpgmConfig.debug('json_database %s' % config.json_database)
            SpgmConfig.debug('json_build_database %s' % config.json_build_database)

            # create output files
            gen.create_output_header(config.declaration_file, config.declaration_include_file)
            gen.create_output_define(config.definition_file)
            # generator.create_output_static(args.output_static)
            # generator.create_output_auto(args.output_auto)

            # write config file and database
            gen.write_json_database(config.json_database, config.json_build_database)

            SpgmConfig.debug_verbose('created %u items from %u include files in %.3f seconds' % (num, include_counter, time.monotonic() - start_time))

        finally:
            SpgmConfig.verbose('Releasing lock...')
            self.lock.release()

    def run_recompile_auto_strings(self, target, source, env):
        SpgmConfig.debug('recompile auto strings')
        SpgmExtraScript._touch_output_files(env)

    # register process nodes for all C/C++ source files
    def register_middle_ware(self, env):

        config = SpgmConfig(env)

        def process_node(node: FS.File):
            if node:
                file = node.srcnode().get_abspath()

                if file==config.declaration_file:
                    return None

                for pattern in config.source_excludes:
                    if fnmatch.fnmatch(file, pattern):
                        return node
                self.source_files.append(node)
                return node
            return None

        for suffix in env['CPPSUFFIXES']:
            env.AddBuildMiddleware(process_node, '*%s' % suffix)

        # def process_linker_node(node: FS.File):
        #     file = node.get_abspath()
        #     print('LINKER %s' % file)

        # for suffix in ['*.o', '*.a']:
        #     env.AddBuildMiddleware(process_linker_node, suffix)

    def add_pre_actions(self, env):
        for source in self.source_files:
            env.AddPreAction(source.get_path() + '.o', self.run_spgm_generator)


if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    SpgmConfig._verbose = True

SpgmConfig.verbose('SPGM PRESCRIPT', True)

if not hasattr(generator, 'spgm_extra_script'):
    SpgmConfig._debug = SpgmConfig(env).enable_debug
    generator.spgm_extra_script = SpgmExtraScript()
    generator.spgm_extra_script.register_middle_ware(env)
    # force recompilation of the auto strings source
    SpgmExtraScript._touch_output_files(env)
