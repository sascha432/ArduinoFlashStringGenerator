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
    _debug = True

    def echo(msg, title=None):
        if title==True:
            n = max(10, (click.get_terminal_size()[0] - len(msg)) // 2)
            click.echo("%s %s %s" % ('-'*n, msg, '-'*n))
        else:
            click.echo(msg)

    def verbose(msg, title=None):
        if SpgmConfig._verbose:
            SpgmConfig.echo(msg, title)

    def debug(msg, title=None):
        if SpgmConfig._debug:
            SpgmConfig.echo(msg, title)


    def __init__(self, env):
        self._env = env
        self.project_src_dir = path.abspath(self._env.subst('$PROJECT_SRC_DIR'))

    def _get_abspath(self, name):
        if path.isabs(name):
            return path.abspath(name) # normalize path
        return path.abspath(path.join(self.project_src_dir, name))

    # def _get_abspath_list(self, list):
    #     parts = [] # type: List[str]
    #     for name in list:
    #         parts.append(self._get_abspath(name))
    #     return parts

    # def _get_pattern_list(self, list):
    #     parts = [] # type: List[str]
    #     for name in list:
    #         if path.isdir(name) and not name.endswith('*'):
    #             name = path.join(name, '*')
    #         parts.append(name)
    #     return parts

    def _get_path(self, name, default=''):
        return self._get_abspath(self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default)))

    def _get_string(self, name, default=''):
        return self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default))

    def _get_bool(self, name, default=None):
        value = self._env.subst(self._env.GetProjectOption('custom_spgm_generator.%s' % name, default=default))
        if isinstance(value, bool) or (isinstance(value, str) and value.lower() in ('true', 'false')):
            return bool(value)
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
            if isinstance(item, str):
                item = self._env.subst(item.strip())
                if item:
                    parts.append((item, '1'))
            elif isinstance(item, (tuple, list)):
                value = self._env.subst(str(item[1]))
                if not value:
                    value = '1'
                parts.append((str(item[0]), value))
        return parts

    @property
    def is_verbose(self):
        return SpgmConfig._verbose

    @property
    def locations_one_per_line(self):
        return self._get_bool('locations_one_per_line', False)

    @property
    def output_language(self):
        return self._subst_list(self._get_string('output_language', 'default'), SplitSepType.WHITESPACE)

    @property
    def definition_file(self):
        return self._get_path('definition_file', '$PROJECT_SRC_DIR/spgm_auto_strings.cpp')

    @property
    def declaration_file(self):
        return self._get_path('declaration_file', '$PROJECT_INCLUDE_DIR/spgm_auto_strings.h')

    @property
    def json_database(self):
        return self._get_path('json_database', '$PROJECT_DIR/spgm_json_database.json')

    @property
    def json_build_database(self):
        return self._get_path('json_build_database', '$BUILD_DIR/spgm_build_database.json')

    @property
    def skip_includes(self):
        return self._subst_list(self._get_string('skip_includes'), SubstListType.PATTERN)

    @property
    def source_excludes(self):
        return self._subst_list(self._get_string('source_excludes'), SubstListType.PATTERN)

    def get_source_excludes(env):
        return SpgmConfig(env).source_excludes

    @property
    def declaration_include_file(self):
        return self._get_string('declaration_include_file', 'spgm_string_generator.h')

    @property
    def defines(self):
        parts = self._normalize_defines_list(self._env['CPPDEFINES']) # List[Tuple[str, str]]
        return parts

    @property
    def include_dirs(self):
        parts = [] # type: List[str]
        parts.extend(self._subst_list(self._get_string('include_dirs'), SubstListType.ABSPATH))
        parts.extend(self._subst_list(self._env['CPPPATH'], SubstListType.ABSPATH))
        parts.extend(self._subst_list(self._env['PROJECT_INCLUDE_DIR'], SubstListType.ABSPATH))
        return parts

# class SpgmProjectConfig(object):
#     def __init__(self, env):
#         self.src_dir = path.abspath(env.subst('$PROJECT_SRC_DIR'))
#         tmp = []
#         tmp = SpgmConfig.normalize_str_list(SpgmConfig.get_spgm_include_dirs(env), self.src_dir)
#         tmp.extend(SpgmConfig.normalize_str_list(env['CPPPATH'], self.src_dir))
#         ip = SpgmConfig.normalize_str_list(env.subst('$PROJECT_INCLUDE_DIR'), self.src_dir)
#         if ip:
#             tmp.extend(ip)
#         else:
#             tmp.append(self.src_dir)
#         self.include_dirs = tmp

#         tmp = env.subst(env.GetProjectOption('custom_spgm_generator.spgm_include_ignore', default=''))
#         tmp = SpgmConfig.normalize_str_list(tmp, self.src_dir)
#         filename = self.config.auto_strings_cpp
#         if not filename in tmp:
#             tmp.append(filename)
#         filename = self.config.auto_strings_header
#         if not filename in tmp:
#             tmp.append(filename)
#         filename = self.config.json_database
#         if not filename in tmp:
#             tmp.append(filename)
#         self.include_ignore = tmp

#         self.cpp_defines = SpgmConfig.normaline_defines_list(self.env.get('$CPPDEFINES'))

#         self.extra_args = []
#         self.source = []

#         self.src_filter = []
#         for filter in SpgmConfig.normalize_str_list(env.subst(' '.join(env.GetProjectOption('src_filter'))), sep='>'):
#             filter = env.subst(filter)
#             if filter:
#                 filter = filter.strip()
#                 if filter:
#                     self.src_filter.append(filter + '>')

# class SpgmLibraryConfig(object):
#     def __init__(self, lib, env):
#         self.src_dir = lib.src_dir
#         tmp = []
#         if lib.include_dir:
#             dir_name = lib.include_dir.strip()
#             if dir_name:
#                 dir_name = SpgmBase.prepend_path(dir_name, lib.src_dir)
#                 if dir_name not in tmp:
#                     tmp.append(dir_name)
#         else:
#             tmp.append(SpgmConfig.prepend_path(lib.src_dir, None))
#         for dir_name in lib.get_include_dirs():
#             if dir_name:
#                 dir_name = dir_name.strip()
#                 if dir_name:
#                     dir_name = SpgmConfig.prepend_path(dir_name, lib.src_dir)
#                     if dir_name not in tmp:
#                         tmp.append(dir_name)
#         self.include_dirs = tmp

#         self.cpp_defines = [] #SpgmBase.normaline_defines_list(lib.cppdefines)

#         self.include_ignore = []
#         self.extra_args = []
#         self.source = []
#         self.src_filter = lib.src_filter

# class SpgmTargetConfig(SpgmConfig):
#     def __init__(self, name, env, lib=None):
#         self._name = name
#         self._env = env
#         if lib:
#             self._target = SpgmLibraryConfig(lib, env)
#         else:
#             self._target = SpgmProjectConfig(env)

#     def match_src_filter(self, file, src_filter: List[str], src_dir):
#         result = FilterType.NO_MATCH
#         file = SpgmConfig.prepend_path(file, src_dir)
#         if not path.isfile(file):
#             return None
#         debug = False
#         for filter in src_filter:
#             pattern = None
#             type = None
#             if filter.endswith('>'):
#                 if filter.startswith('+<'):
#                     pattern = filter[2:-1]
#                     type = FilterType.INCLUDE
#                 elif filter.startswith('-<'):
#                     pattern = filter[2:-1]
#                     type = FilterType.EXCLUDE
#             if pattern==None:
#                 raise RuntimeError('invalid filter: %s' % filter)
#             else:
#                 is_dir = pattern.endswith('/') or pattern.endswith('\\') or pattern.endswith('.')
#                 pattern = SpgmConfig.prepend_path(pattern, src_dir)
#                 if is_dir and not pattern.endswith('*'):
#                     pattern += os.sep + '*'

#             if fnmatch.fnmatch(file, pattern):
#                 result = type

#             if debug:
#                 def ll(s):
#                     if len(s)>80:
#                         return s[-80:]
#                     return s
#                 print('fnmatch(%s, %s)=%s end result=%s' % (ll(file), ll(pattern), type, result))

#         if debug:
#             print('match_src_filter %s=%s' % (file, result))
#         return result

#     def filter_sources(self, src_filter: List[str], src_dir, source_files: List[str]):
#         tmp = []
#         for source in source_files:
#             if self.match_src_filter(source, src_filter, src_dir)==FilterType.INCLUDE:
#                 tmp.append(source)
#         self.source = tmp
#         return self.source

#     @property
#     def name(self):
#         if self._name==None:
#             return '<project>'
#         return '<library %s>' % self._name
