#
# Author: sascha_lammers@gmx.de
#

import os
from os import path
import json
import time
import sys
import fnmatch
import enum
import hashlib
import glob
from typing import Generic, Generator, Iterable, NewType, Sequence, List, Dict, Tuple, Union

# File.COMPARE
class CompareType(enum.Enum):
    MODIFIED_TIMESTAMP = 'MODIFIED_TIMESTAMP'
    HASH = 'HASH'

# Path.STORE_PATH
class PathType(enum.Enum):
    NORM_PATH = 'NORM_PATH'
    ABS_PATH = 'ABS_PATH'
    REAL_PATH = 'REAL_PATH'

class FilterType(enum.Enum):
    NO_MATCH = 'NO_MATCH'
    INCLUDE = 'INCLUDE'
    EXCLUDE = 'EXCLUDE'

# class ModifiedType(enum.Enum):
#     UNMODIFIED = 'UNMODIFIED'
#     MODIFIED = 'MODIFIED'
#     NEW = 'NEW'
#     REMOVED = 'REMOVED'

#     def __str__(self):
#         return str(self.value).split('.')[-1].lower()

#     def short_str(self):
#         if self==ModifiedType.UNMODIFIED:
#             return '.'
#         if self==ModifiedType.MODIFIED:
#             return '*'
#         if self==ModifiedType.NEW:
#             return '+'
#         if self==ModifiedType.REMOVED:
#             return '-'

class Path(object):

    STORE_PATH = PathType.NORM_PATH

    def normalize(name):
        if name==None:
            return None
        if isinstance(name, list):
            for idx, item in enumerate(name):
                name[idx] = Path.normalize(item)
            return
        if Path.STORE_PATH==PathType.ABS_PATH:
            return path.abspath(name)
        if Path.STORE_PATH==PathType.REAL_PATH:
            return path.realpath(name)
        return path.normpath(name)

    def normpath(name):
        if isinstance(name, list):
            for idx, item in enumerate(name):
                name[idx] = Path.normpath(item)
            return
        return path.normpath(name)

class OutputFiles(object):
    def __init__(self, declare=None, define=None, static=None):
        self.declare = Path.normalize(declare)
        self.define = Path.normalize(define)
        self.static = Path.normalize(static)

    def _todict(self):
        return {
            'declare': self.declare,
            'define': self.define,
            'static': self.static
        }

    def _fromdict(dict):
        return OutputFiles(dict['declare'], dict['define'], dict['static'])

    def exist(self):
        return path.isfile(self.declare) and path.isfile(self.define) and path.isfile(self.static)

class Database(object):
    def __init__(self):
        self._files = {}
        self._includes = []
        self._defines = {}
        self._filter_includes = []
        self._filter_excludes = []
        self._output_files = OutputFiles()

    @property
    def files(self) -> Dict[str, Dict[str, str]]:
        return self._database._files

    @property
    def includes(self) -> List[str]:
        return self._includes

    @property
    def defines(self) -> Dict[str, str]:
        return self._defines

    @property
    def filter_excludes(self) -> List[str]:
        return self._filter_excludes

    @property
    def filter_includes(self) -> List[str]:
        return self._filter_includes

    @property
    def output_files(self) -> OutputFiles:
        return self._output_files

class FileCollector(object):

    COMPARE = CompareType.MODIFIED_TIMESTAMP

    def __init__(self, database_file, config_file, verbose=False):
        self.verbose = verbose
        self.config_file = config_file
        self.database_file = database_file
        self._database = Database()
        self.modified_files = {}
        self._includes = []

    @property
    def modified(self):
        return self._modified

    @property
    def database(self) -> Database:
        return self._database

    @property
    def files(self) -> Dict[str, Dict[str, str]]:
        return self._database._files

    @property
    def output_files(self):
        return self._database._output_files

    @output_files.setter
    def output_files(self, values):
        self._output_files = OutputFiles(values[0], values[1], values[2])

    def hash_file(self, name, file):
        if FileCollector.COMPARE==CompareType.HASH:
            with open(name, 'rb') as f:
                hash = hashlib.sha1(f.read())
                file['hash'] = hash.hexdigest()
        return file

    def prepend_dir(dir, file):
        if dir and not path.isabs(file):
            file = path.join(dir, file)
        return Path.normalize(file)

    def is_different(self, item1, item2):
        return json.dumps(item1, sort_keys=True)!=json.dumps(item2, sort_keys=True)

    # parse args.define and add preprocessor defines
    def parse_defines(self, args_define):
        self._defines = {}
        for define in args_define:
            if '=' not in define:
                value = '1'
            else:
                define, value = define.split('=', 2)
                if len(value)>=4 and value.startswith('\\"') and value.endswith('\\"'): # replace \" surrounding with "
                    value = value[1:-2] + '"'
            self._defines[define] = value

    # add include path
    def add_include(self, dir):
        dir = Path.normalize(dir)
        if dir not in self._includes:
            if self.verbose:
                print('add include path: %s' % dir)
            self._includes.append(dir)

    def glob_recursive(self, dir):
        return glob.glob(dir)

    # add all files from dir with the given extensions
    def add_dir(self, dir, extensions):
        dir = Path.normalize(dir)
        pattern = path.join(dir.rstrip('*'), '.')
        if not glob.glob(pattern, recursive=False):
            raise RuntimeError('not a directory: %s: pattern: %s' % (dir, pattern))

        recursive = False
        if dir.endswith('*'):
            dir += '*'
            recursive = True
        elif not dir.endswith('/') and not dir.endswith('\\') and not dir.endswith('.'):
            dir = path.join(dir, '*')
        if '**' in dir:
            recursive = True

        for file in glob.glob(dir, recursive=recursive):
            for ext in extensions:
                if file.endswith(ext) and path.isfile(file) and self.check_filters(path.dirname(file), True)==FilterType.INCLUDE:
                    self.add_file(file)

    # add single file
    def add_file(self, filename):
        filename = Path.normalize(filename)
        if not path.isfile(filename):
            raise RuntimeError('not a file: %s' % filename)
        if self.check_filters(filename, False)==FilterType.INCLUDE:
            stat = os.stat(filename)
            file = {'size': stat.st_size, 'mtime': stat.st_mtime}
            self._files[filename] = self.hash_file(filename, file)

    def prepare_filter_path(self, name, base_path, type):
        # get trailing slash or backslash before normalizing
        is_dir = name.endswith('/') or name.endswith('\\')
        if base_path and not path.isabs(name):
            name = path.join(base_path, name)
        name = Path.normalize(name)
        if is_dir:
            if type=='exclude':
                # add * or replace . for directories to exclude subdirectories
                if path.basename(name)=='.':
                    name = path.join(path.dirname(name), '*')
                elif path.basename(name)!='*':
                    name = path.join(name, '*')
            elif type=='include':
                # add . to directories
                name = path.join(name, '.')
        return name

    # add file or directory to the source exclude filter
    def add_src_filter_include(self, name, base_path=None):
        self._filter_includes.append(self.prepare_filter_path(name, base_path, 'include'))

    # add file or directory to the source include filter
    def add_src_filter_exclude(self, name, base_path=None):
        self._filter_excludes.append(self.prepare_filter_path(name, base_path, 'exclude'))

    # read database
    def read_database(self):
        self._modified = False
        self._database = Database()
        self._files = {}
        self._includes = []
        self._filter_includes = []
        self._filter_excludes = []
        if not self.database_file:
            if self.verbose:
                print('database filename not set')
            self._modified = True
            return
        if not path.exists(self.database_file):
            if self.verbose:
                print('database does not exist')
            self._modified = True
            return
        with open(self.database_file, 'rt') as f:
            contents = f.read()
            contents = contents.strip()
            if contents:
                database = json.loads(contents)
                try:
                    files = {}
                    for name, item in database['files'].items():
                        files[Path.normalize(name)] = item

                    self._database._files = files
                    self._database._includes = Path.normalize(database['includes'])
                    self._database._defines = database['defines']
                    self._database._filter_includes = Path.normpath(database['filters']['include'])
                    self._database._filter_excludes = Path.normpath(database['filters']['exclude'])
                    self._database._output_files = OutputFiles._fromdict(database['output_files'])

                except KeyError as e:
                    if self.verbose:
                        print('ignoring error %s' % e)
                    pass

    # write database
    def write_database(self):
        if not self.database_file:
            if self.verbose:
                print('database filename not set')
            return
        database = {
            'files': self._database._files,
            'includes': self._database._includes,
            'defines': self._database._defines,
            'filters': {
                'include': self._database._filter_includes,
                'exclude': self._database._filter_excludes
            },
            'output_files': self._database._output_files._todict()
        }
        # files = database['files']
        # for path, file in self._database_files:
        #     files[path] = file._todict()

        with open(self.database_file, 'wt') as f:
            f.write(json.dumps(database, indent=4))

    # update database and mark as modified if there were any changes
    def update_database(self):
        if self.is_different(self._files, self.database._files):
            if self.verbose:
                print('files have been modified')
            self._modified = True
            for name, item in self._files.items():
                if name in self.database._files:
                    if self.is_different(item, self.database._files[name]):
                        self.modified_files[name] = item
                    if self.verbose:
                        print('modified: %s' % name)
                else:
                    self.modified_files[name] = item
                    if self.verbose:
                        print('new: %s' % name)
            self.database._files = self._files
        if self.is_different(self._includes, self.database._includes):
            if self.verbose:
                print('includes have been modified')
            self._modified = True
            self.database._includes = self._includes
        if self.is_different(self._defines, self.database._defines):
            if self.verbose:
                print('defines have been modified')
            self._modified = True
            self.database._defines = self._defines
        if self.is_different(self._filter_includes, self.database._filter_includes):
            if self.verbose:
                print('filter includes have been modified')
            self._modified = True
            self.database._filter_includes = self._filter_includes
        if self.is_different(self._filter_excludes, self.database._filter_excludes):
            if self.verbose:
                print('filter excludes have been modified')
            self._modified = True
            self.database._filter_excludes = self._filter_excludes
        if self.is_different(self._output_files._todict(), self.database._output_files._todict()):
            if self.verbose:
                print('output files have changed')
            self._modified = True
            self.database._output_files = self._output_files
            self.modified = True
        elif not self._output_files.exist():
            if self.verbose:
                print('output files do not exist')
            self.modified = True

        del self._files
        del self._includes
        del self._defines
        del self._filter_includes
        del self._filter_excludes
        del self._output_files

    # check if a file or directory matches the source filter
    def check_filters(self, name, is_dir):
        debug = False
        if is_dir:
            name = os.path.join(name, '.')
        # path_parts = self.create_compare_partial_path_parts(path)
        filter = FilterType.NO_MATCH
        for filter_path in self._filter_includes:
            if debug:
                print('include %s=%s pattern=%s' % (name, fnmatch.fnmatch(name, filter_path), filter_path))
            if fnmatch.fnmatch(name, filter_path):
                filter = FilterType.INCLUDE
                break
        for filter_path in self._filter_excludes:
            if debug:
                print('exclude %s=%s pattern=%s' % (name, fnmatch.fnmatch(name, filter_path), filter_path))
            if fnmatch.fnmatch(name, filter_path):
                filter = FilterType.EXCLUDE
                break
        if debug:
            print('filter=%s is_dir=%s path=%s' % (filter, is_dir, name))
        return filter
