#
# Author: sascha_lammers@gmx.de
#

from .types import SubstListType, SplitSepType, CompressionType
from .cache import SpgmCache
from os import path
from typing import List, Tuple
import fnmatch
import enum
import re
import click
import glob

class SpgmConfig(SpgmCache):

    #
    # static methods for terminal suppprt and debugging
    #

    _verbose = False
    _debug = False

    def echo(msg, title=None):
        if title==True:
            if msg!='':
                msg = ' %s ' % msg
            cols = click.get_terminal_size()[0]
            n = max(10, (cols - len(msg) - 1) // 2)
            m = (cols - n - len(msg) - 1)
            if m<=5:
                n -= 5
                m = 5
            click.echo(('-' * n) + msg + ('-' * m))
        else:
            click.echo(msg)

    def verbose(msg, title=None):
        if SpgmConfig._verbose:
            SpgmConfig.echo(msg, title)

    def debug(msg, title=None):
        if SpgmConfig._debug:
            SpgmConfig.echo(msg, title)

    def debug_verbose(msg, title=None):
        if SpgmConfig._debug:
            SpgmConfig.debug(msg, title)
        elif SpgmConfig._verbose:
            SpgmConfig.verbose(msg, title)

    def box(msgs, fg=None):
        if isinstance(msgs, str):
            msgs = (msgs,)
        click.secho('-'*76)
        for msg in msgs:
            if isinstance(msg, tuple):
                click.secho(msg[0], fg=msg[1])
            else:
                click.secho(msg, fg=fg)
        click.secho('-'*76)

    #
    # Config class
    #
    def __init__(self, env):
        SpgmCache.__init__(self, env)
        self.project_src_dir = self.cache('project_src_dir', lambda: path.abspath(self._env.subst('$PROJECT_SRC_DIR')))
        self.project_dir = self.cache('project_dir', lambda: path.abspath(self._env.subst('$PROJECT_DIR')))

    def _get_abspath(self, name):
        if path.isabs(name):
            return path.abspath(name) # normalize path
        return path.abspath(path.join(self.project_src_dir, name))

    def _get_path(self, name, default=''):
        return self._get_abspath(self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default)))

    def _get_string(self, name, default=''):
        return self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default))

    def _get_bool(self, name, default=None):
        value = self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default))
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value!=0
        if isinstance(value, str):
            lvalue = value.lower()
            if lvalue in('true', '1'):
                return True
            if lvalue in('false', '0'):
                return False
        raise RuntimeError('custom_spgm_generator.%s: expected true or false, got %s' % (name, value))

    def _subst_list(self, list, type=SubstListType.STR, sep=SplitSepType.NEWLINE) -> List[str]:
        parts = []
        if not list:
            return parts
        if isinstance(list, str):
            list = re.split(sep.value, list)
        for part in list:
            part = self._env.subst(part).strip()
            if part:
                if type in(SubstListType.ABSPATH, SubstListType.PATTERN):
                    part = self._get_abspath(part)
                if type==SubstListType.PATTERN:
                    if path.isdir(part) and not part.endswith('*'):
                        part = path.join(part, '*')
                parts.append(part)
        return parts

    def _normalize_defines_list(self, defines) -> List[Tuple[str, str]]:
        if isinstance(defines, str):
            defines = defines.split('\n')
        parts = []
        if not defines:
            return parts
        for item in defines:
            value = None
            if isinstance(item, str):
                item = self._env.subst(item.strip())
                if item:
                    value = '1'
                    if '=' in item:
                        item2, value = item.split('=', 3)
                        if '"' in item2 or "'" in  item2:
                            raise RuntimeError('constant name contains quotes: %s' % (item))
                        item = item2.strip()
                        if item:
                            value = value.strip() # type: str
                            if not value:
                                value = '1'
            elif isinstance(item, (tuple, list)):
                value = self._env.subst(str(item[1]))
                if not value:
                    value = '1'
                item = str(item[0])
            if value!=None:
                if value.startswith('\\"') and value.endswith('\\"'):
                    value = '"' + value[2:-2] + '"'
                if value.startswith('"') and value.endswith('"'):
                    value = value.replace('\\ ', ' ')

                parts.append((item, value))
        return parts

    @property
    def is_verbose(self):
        return SpgmConfig._verbose

    @property
    def locations_one_per_line(self):
        return self.cache('locations_one_per_line', lambda: self._get_bool('locations_one_per_line', False))

    @property
    def enable_debug(self):
        return self.cache('enable_debug', lambda: self._get_bool('enable_debug', False))

    @property
    def add_unused(self):
        return self.cache('add_unused', lambda: self._get_bool('add_unused', False))

    @property
    def build_database_compression(self):
        return self.cache('build_database_compression', lambda: CompressionType.fromString(self._get_string('build_database_compression', 'none')))

    @property
    def output_language(self):
        return self.cache('output_language', lambda: self._subst_list(self._get_string('output_language', 'default'), SplitSepType.WHITESPACE))

    @property
    def auto_run(self):
        auto_run = self.cache('auto_run', lambda: self._get_string('auto_run', 'always').strip().lower())
        auto_run_options = ['always', 'never', 'rebuild']
        if auto_run in auto_run_options:
            return auto_run
        raise RuntimeError('Invalid setting for custom_spgm_generator.auto_run: got %s: expected %s' % (auto_run, auto_run_options))

    @property
    def is_first_run(self):
        return not (path.isfile(self.declaration_file) and path.isfile(self.definition_file))

    @property
    def is_clean(self):
        return len(glob.glob(path.join(self.build_database_dir, 'database.pickle*'))) == 0

    @property
    def definition_file(self):
        return self.cache('definition_file', lambda: self._get_path('definition_file', '$PROJECT_SRC_DIR/spgm_auto_strings.cpp'))

    @property
    def declaration_file(self):
        return self.cache('declaration_file', lambda: self._get_path('declaration_file', '$PROJECT_INCLUDE_DIR/spgm_auto_strings.h'))

    @property
    def statics_file(self):
        return self.cache('statics_file', lambda: self._get_path('statics_file', '$PROJECT_INCLUDE_DIR/spgm_static_strings.h'))

    @property
    def auto_defined_file(self):
        return self.cache('auto_defined_file', lambda: self._get_path('auto_defined_file', '$PROJECT_INCLUDE_DIR/spgm_auto_defined.h'))

    @property
    def build_database_dir(self):
        return self.cache('build_database_dir', lambda: self._get_path('build_database_dir', '$BUILD_DIR/spgm'))

    @property
    def skip_includes(self):
        return self.cache('skip_includes', lambda: self._subst_list('%s\n%s' % (self.declaration_file,  self._get_string('skip_includes')), SubstListType.PATTERN))

    @property
    def source_excludes(self):
        return self.cache('source_excludes', lambda: self._subst_list(self._get_string('source_excludes'), SubstListType.PATTERN))

    @property
    def declaration_include_file(self):
        return self.cache('declaration_include_file', lambda: self._get_string('declaration_include_file', 'spgm_string_generator.h'))

    @property
    def defines(self):
        return self.cache('defines', lambda: self._normalize_defines_list(self._env['CPPDEFINES']))

    @property
    def pcpp_bin(self):
        return self.cache('pcpp_bin', lambda: self._get_path('pcpp_bin', '$PYTHONEXE $PROJECT_DIR/scripts/pcpp_cli.py'))

    @property
    def pcpp_defines(self):
        return self.cache('pcpp_defines', lambda: self._normalize_defines_list(self._get_string('pcpp_defines')))

    def get_include_dirs(self):

        if self.is_cached('include_dirs'):
            return (self.get_cache('include_dirs'), [])

        parts = [] # type: List[str]
        parts.extend(self._subst_list(self._get_string('include_dirs'), SubstListType.ABSPATH))

        cpp_path = self._subst_list(self._env['CPPPATH'], SubstListType.ABSPATH)
        project_include_dir = self._get_abspath(self._env['PROJECT_INCLUDE_DIR'])

        # add include_path for declaration_file
        add_path = []
        if not path.dirname(self.declaration_file) in cpp_path:
            add_path.append(path.dirname(self.declaration_file))

        # add include_path for declaration_include_file
        dir = self.declaration_include_file
        if not path.isabs(dir):
            dir = path.dirname(path.join(project_include_dir, dir))
        dir = path.abspath(dir)
        if not dir in cpp_path and not dir in add_path:
            add_path.append(dir)
        if add_path:
            self._env.Replace(BUILD_FLAGS=self._env['BUILD_FLAGS'] + ['-I%s' % path for path in add_path])
            self._env.Replace(CPPPATH=self._env['CPPPATH'] + add_path)
            cpp_path = self._subst_list(self._env['CPPPATH'], SubstListType.ABSPATH)
            SpgmConfig.debug('added %s to %s' % (add_path, cpp_path))

        parts.extend(cpp_path)
        parts.append(project_include_dir)

        self.set_cache('include_dirs', parts)

        return (parts, add_path)

    @property
    def include_dirs(self):
        return self.get_include_dirs()[0]

    def is_source_excluded(self, file):
        for exclude in self.source_excludes:
            # SpgmConfig.debug('fnmatch (%s, %s) = %s' % (file, exclude, fnmatch.fnmatch(file, exclude)))
            if fnmatch.fnmatch(file, exclude):
                return True
        return False
