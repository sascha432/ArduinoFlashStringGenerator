#
# Author: sascha_lammers@gmx.de
#

import builtins
import os
import copy
import fnmatch
from os import path
from . import *
from typing import List, Tuple
import enum
import re
import click
from pathlib import Path, PureWindowsPath

# class SpgmBase(object):

#     def _dump(node, path=[], objs=[]):
#         objs.append(id(node))
#         for name in dir(node):
#             if not name.startswith('__'):
#                 if hasattr(node, name):
#                     attr = getattr(node, name)
#                     if not id(attr) in objs:
#                         tmp = copy.copy(path)
#                         tmp.append(name)
#                         print('%s %s' % ('.'.join(tmp), str(attr)))
#                         SpgmBase._dump(attr, tmp, objs)

#     # def get_spgm_include_dirs(env):
#     #     return path.abspath(env.subst(env.GetProjectOption('custom_spgm_generator.spgm_include_dirs', default='')))

#     # def get_spgm_extra_args(env):
#     #     return SpgmBase.normalize_str_list(env.subst(env.GetProjectOption('custom_spgm_generator.extra_args', default='')))

#     # change directory of path to absolute and if is a directory, append /.
#     def _abspath(path_name, append_to_dir='.'):
#         path_name = path.abspath(path_name)
#         if path_name.endswith('*') or not path.isdir(path_name):
#             return path_name
#         return path.join(path_name, append_to_dir)

#     def abspath(items):
#         if isinstance(items, str):
#             return SpgmBase._abspath(items)
#         tmp = []
#         for item in items:
#             tmp.append(SpgmBase.abspath(item))
#         return tmp

    # def normalize_defines_list(defines) -> List[Tuple[str, str]]:
    #     if isinstance(defines, str):
    #         defines = defines.split('\n')
    #     parts = []
    #     if not defines:
    #         return parts
    #     for item in defines:
    #         if isinstance(item, str):
    #             item = item.strip()
    #             if item:
    #                 parts.append((item, '1'))
    #         elif isinstance(item, (tuple, list)):
    #             parts.append((str(item[0]), str(item[1])))
    #     return parts

    # def normalize_path_pattern_list(path_patterns):
    #     parts = [] # type: List[str]
    #     for name in path_patterns:
    #         name = path.abspath(name) # type: str
    #         if path.isdir(name) and not name.endswith('*'):
    #             name = path.join(name, '*')
    #         parts.append(name)
    #     return parts

class SubstListType(enum.Enum):
    STR = 'str'
    ABSPATH = 'abspath'
    PATTERN = 'pattern'

class SplitSepType(enum.Enum):
    NEWLINE = r'[\r\n]'
    WHITESPACE = r'\s'

class SpgmConfig(object):

    _verbose = False
    _debug = False
    _cache = {}

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

    def __cache(name, lazy_load):
        if not name in SpgmConfig._cache:
            # SpgmConfig.debug('creating cache entry for %s' % name)
            SpgmConfig._cache[name] = lazy_load()
        return SpgmConfig._cache[name]

    def _cache_item_name(self, name):
        return 'env_%s_item_%s' % (id(self._env), name)

    def cache(self, name, lazy_load):
        return SpgmConfig.__cache(self._cache_item_name(name), lazy_load)

    def is_cached(self, name):
        return self._cache_item_name(name) in SpgmConfig._cache

    def get_cache(self, name):
        name = self._cache_item_name(name)
        if not name in SpgmConfig._cache:
            # SpgmConfig.debug('cache entry for %s is empty' % name)
            return None
        # SpgmConfig.debug('getting cache for %s' % name)
        return SpgmConfig._cache[name]

    def set_cache(self, name, value):
        # SpgmConfig.debug('setting cache for %s' % name)
        name = self._cache_item_name(name)
        SpgmConfig._cache[name] = value


    def __init__(self, env):
        self._env = env
        self.project_src_dir = self.cache('project_src_dir', lambda: path.abspath(self._env.subst('$PROJECT_SRC_DIR')))
        self.project_dir = self.cache('project_dir', lambda: path.abspath(self._env.subst('$PROJECT_DIR')))

    # def _make_relative_to(source_path, target_path):
    #     source_path = path.abspath(source_path)
    #     target_path = path.abspath(target_path)
    #     if PureWindowsPath(source_path).drive!=PureWindowsPath(target_path).drive:
    #         raise RuntimeError('cannot create relative path of %s to %s' % (source_path, target_path))
    #     if source_path==target_path:
    #         return source_path
    #     source = Path(source_path).parts
    #     full_source = source
    #     target = Path(target_path).parts
    #     full_target = target
    #     make_relative = []

    #     num = min(len(source), len(target))
    #     for n in range(1, num + 2):
    #         if path.join(*source[0:n])!=path.join(*target[0:n]):
    #             num = n
    #             make_relative = ['..']*(len(full_source) - n + 2)
    #             break
    #     npl = list(full_source) + make_relative + list(full_target[num:])
    #     # np = path.join(*npl)
    #     # anp = path.abspath(np)
    #     diff = len(full_target) - (len(full_source) - len(make_relative) + len(full_target) - num + 1)
    #     # diff = len(full_target) - len(Path(anp).parts)
    #     # print(diff)
    #     if diff>=1:
    #         diff -= 1
    #         make_relative = make_relative[0:-1]
    #         npl = list(full_source) + make_relative + list(full_target[num - diff:])

    #     np = path.join(*npl)
    #     # anp = path.abspath(np)
    #     # print(anp)

    #     if path.abspath(np)==target_path:
    #         return path.normpath(np)
    #     raise RuntimeError('cannot create relative path of %s to %s' % (source_path, target_path))

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
    def is_clean(self):
        return not path.isfile(self.json_build_database)

    @property
    def is_first_run(self):
        return not (path.isfile(self.declaration_file) and path.isfile(self.definition_file))

    @property
    def definition_file(self):
        return self.cache('definition_file', lambda: self._get_path('definition_file', '$PROJECT_SRC_DIR/spgm_auto_strings.cpp'))

    @property
    def declaration_file(self):
        return self.cache('declaration_file', lambda: self._get_path('declaration_file', '$PROJECT_INCLUDE_DIR/spgm_auto_strings.h'))

    @property
    def json_database(self):
        return self.cache('json_database', lambda: self._get_path('json_database', '$PROJECT_DIR/spgm_json_database.json'))

    @property
    def json_build_database(self):
        return self.cache('json_build_database', lambda: self._get_path('json_build_database', '$BUILD_DIR/spgm_build_database.json'))

    @property
    def log_file(self):
        return self.cache('log_file', lambda: self._get_path('log_file', '$BUILD_DIR/spgm_string_generator.log'))

    @property
    def skip_includes(self):
        return self.cache('skip_includes', lambda: self._subst_list('%s\n%s' % (self.declaration_file,  self._get_string('skip_includes')), SubstListType.PATTERN))

    @property
    def source_excludes(self):
        return self.cache('source_excludes', lambda: self._subst_list(self._get_string('source_excludes'), SubstListType.PATTERN))
#        return self.cache('source_excludes', lambda: self._subst_list('%s\n%s\n%s' % (self.definition_file, self.declaration_file, self._get_string('source_excludes')), SubstListType.PATTERN))

    @property
    def declaration_include_file(self):
        return self.cache('declaration_include_file', lambda: self._get_string('declaration_include_file', 'spgm_string_generator.h'))

    @property
    def defines(self):
        return self.cache('defines', lambda: self._normalize_defines_list(self._env['CPPDEFINES']))

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
