#
# Author: sascha_lammers@gmx.de
#

from SCons.Script import ARGUMENTS
from SCons.Node import FS
from SCons.Script.SConscript import SConsEnvironment, DefaultEnvironmentCall
from SCons.Script import COMMAND_LINE_TARGETS
# from SCons.Script.SConscript import DefaultEnvironmentCall
import os
from os import path
import sys
import inspect
import tempfile
import shlex
import subprocess
import fnmatch
from generator import ExportType, ItemType, SpgmConfig, Item, Generator, SpgmPreprocessor
import threading
import generator
from typing import List
from pathlib import Path
import pickle
import json
import struct
import enum
import tempfile
import time
import click

env = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("env")

class SpgmExtraScript(object):

    def __init__(self):
        self.verbose = SpgmConfig._verbose
        self._source_files = []

    #
    # Setup SPGM builder
    #
    def init_spgm_build(self, env):
        SpgmConfig.debug('init_spgm_build', True)
        for env in ([env] + [builder.env for builder in env.GetLibBuilders()]):
            # print(dir(builder.env))
            config = SpgmConfig(env)
            if not config.is_source_excluded(config.project_src_dir):
                include_dirs, paths_added = config.get_include_dirs()
                SpgmConfig.debug('added include_dirs %s' % paths_added)
            else:
                SpgmConfig.debug('project_src_dir %s is excluded, skipping include_dirs' % config.project_src_dir)
    #
    # install pcpp
    #
    def run_install_requirements(self, source, target, env):
        # env.Execute("$PYTHONEXE -m pip install --upgrade pip")
        env.Execute("$PYTHONEXE -m pip install pcpp==1.22")

        version = None
        try:
            from pcpp.preprocessor import Preprocessor, OutputDirective, Action
            import pcpp
            version = pcpp.__version__
        except Exception as e:
            SpgmConfig.box('Installation was not succesful. %s' % e, fg='red')
            env.Exit(1)

        if version=='1.22':
            SpgmConfig.box('Requirements have been successfully installed', fg='green')
        else:
            SpgmConfig.box((('Requirements have been installed.', 'green'), ('Warning: version mismatch pcpp==%s not 1.22 - If any issues occur, try to install the correct version' % version, 'yellow')))

    #
    # register process nodes for all C/C++ source files
    #
    def register_middle_ware(self, env):
        config = SpgmConfig(env)
        def process_node(node: FS.File):
            if node:
                file = node.srcnode().get_abspath()
                # # # ignore declaration file to avoid a rebuild every time it is changed
                # if file==config.declaration_file:
                #     return None
                if file==config.definition_file:
                    self._auto_strings_target = node
                    return node
                for pattern in config.source_excludes:
                    if fnmatch.fnmatch(file, pattern):
                        return node
                self._source_files.append(node)
                return node
            return None

        for suffix in ['c', 'C', 'cc', 'cpp', 'ino', 'INO']:
            env.AddBuildMiddleware(process_node, '*.' + suffix)

    #
    # add all PreActions for source and binary
    #
    def add_pre_actions(self, env):
        SpgmConfig.debug('spgm_extra_script.add_pre_actions', True)
        if self._source_files:
            for node in self._source_files:
                # add pre actions for every target to be scanned
                env.AddPreAction(node.get_path() + '.o', self.run_spgm_generator)
                # add all source files to the requirements of the definition file
                # to compile it after collection all strings
                env.Requires(self._auto_strings_target.get_path() + '.o', node.get_path() + '.o')

        # env.AddPreAction(env.get("PIOMAINPROG"), spgm_extra_script.run_mainprog)

    # #
    # # force rebuild of mainprog
    # #
    # def run_mainprog(self, target, source, env):
    #     config = SpgmConfig(env)
    #     # append new line to change file modification time and hash
    #     with open(config.definition_file, 'at') as file:
    #         file.write('\n')

    #
    # Run SPGM generator on given target
    #
    def run_spgm_generator(self, target, source, env):

        start_time = time.monotonic()
        config = SpgmConfig(env)

        target_path = target[0].get_abspath()

        # create list of all files
        SpgmConfig.debug('source files', True)
        files = []
        for node in source:
            file = node.get_abspath()
            if file!=config.definition_file and not config.is_source_excluded(file):
                SpgmConfig.debug('source %s' % file)
                files.append((file, node.get_path()))
                print('Preprocessing %s' % node.get_path())

        if not files:
            SpgmConfig.debug('no files for %s' % target)
            return

        # create generator
        SpgmConfig.debug('creating generator object', True)
        gen = Generator(config, files, target, env)
        gen.language = config.output_language


        # create config preprocessor
        data = {
            'target': gen._database.get_target(),
            'files': gen.files,
            'defines': config.defines,
            'pcpp_defines': config.pcpp_defines,
            'include_dirs': config.include_dirs,
            'skip_includes': config.skip_includes
        }
        try:
            with tempfile.NamedTemporaryFile('wt', delete=False) as file:
                file.write(json.dumps(data))
                tmpfile = file.name

            args = config.pcpp_bin.split(' ')
            args += ['--file', tmpfile]
            if SpgmConfig._verbose:
                args.append('--verbose')
                # display all output
                proc = subprocess.Popen(args, text=True)
                result =proc.wait(timeout=300)
                errs = ''
            else:
                # collect stderr output and display on error
                proc = subprocess.Popen(args, text=True, stderr=subprocess.PIPE)
                outs, errs = proc.communicate(timeout=300)
                result = proc.returncode

            if result!=0:
                print(errs, file=sys.stderr)
                raise RuntimeError('processor failed with exit code %u. cmd:\n%s\n' % (result, ' '.join(args)))

            with open(tmpfile, 'rt') as file:
                output = json.loads(file.read())

            # output['files']: all files processed
            # output['files_hash']: hash of processed files to detect changes
            # output['items']: items found in the files

            gen._database.add_target_files(output['files'], output['files_hash'])

            gen.copy_to_database(output['items'])
            SpgmConfig.debug('creating output files', True)

            num = len(output['items'])
            include_counter = len(output['files'])

            SpgmConfig.debug('output_language %s' % gen.language)
            SpgmConfig.debug('declaration_file %s' % config.declaration_file)
            SpgmConfig.debug('definition_file %s' % config.definition_file)
            SpgmConfig.debug('declaration_include_file %s' % config.declaration_include_file)

            # create output files

            gen.create_output_header(config.declaration_file, config.declaration_include_file)
            gen.create_output_define(config.definition_file)
            gen.create_output_static(config.statics_file)
            gen.create_output_auto_defined(config.auto_defined_file)

            SpgmConfig.debug_verbose('created %u items from %u include files in %.3f seconds' % (num, include_counter, time.monotonic() - start_time))

        finally:
            os.unlink(tmpfile);


    #
    # run SPGM generator on target
    #
    def run_spgm_build(self, target, source, env):
        self.add_pre_actions(env)

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    SpgmConfig._verbose = True

SpgmConfig.verbose('SPGM PRESCRIPT', True)

if not hasattr(generator, 'spgm_extra_script'):
    SpgmConfig._debug = SpgmConfig(env).enable_debug
    generator.spgm_extra_script = SpgmExtraScript()

spgm_extra_script = generator.spgm_extra_script

env.AddCustomTarget("spgm_build", [env.get("PIOMAINPROG")], [], title="build spgm strings", description=None, always_build=False)
env.AddCustomTarget("spgm_install_requirements", None, [ lambda target, source, env: click.secho('Installing requirements for SPGM generator...', fg='yellow') ], title="install requirements", description="install requirements for SPGM generator", always_build=True)

spgm_extra_script.register_middle_ware(env)
