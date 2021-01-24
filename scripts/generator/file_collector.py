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

# File.COMPARE
class CompareType(enum.Enum):
    MODIFIED_TIMESTAMP = 'MODIFIED_TIMESTAMP'
    HASH = 'HASH'

# FileCollector.STORE_PATH
class PathType(enum.Enum):
    RELATIVE_PATH = 'RELATIVE_PATH'
    ABS_PATH = 'ABS_PATH'
    REAL_PATH = 'REAL_PATH'

class FilterType(enum.Enum):
    NO_MATCH = 'NO_MATCH'
    INCLUDE = 'INCLUDE'
    EXCLUDE = 'EXCLUDE'

class ModifiedType(enum.Enum):
    UNMODIFIED = 'UNMODIFIED'
    MODIFIED = 'MODIFIED'
    NEW = 'NEW'
    REMOVED = 'REMOVED'

    def __str__(self):
        return str(self.value).split('.')[-1].lower()

    def short_str(self):
        if self==ModifiedType.UNMODIFIED:
            return '.'
        if self==ModifiedType.MODIFIED:
            return '*'
        if self==ModifiedType.NEW:
            return '+'
        if self==ModifiedType.REMOVED:
            return '-'

class OutputFiles(object):
    def __init__(self, declare, define, static):
        self.declare = declare
        self.define = define
        self.static = static

    def _todict(self):
        return {
            'declare': self.declare,
            'define': self.define,
            'static': self.static
        }

class File(object):

    COMPARE = CompareType.HASH

    def __init__(self, file, size=None, mtime=None, hash=None, type=ModifiedType.UNMODIFIED):
        self.file = file
        self.type = type
        self.size = size
        self.mtime = mtime
        self.hash = hash

    def hash_file(self):
        if self.COMPARE==CompareType.HASH:
            with open(self.file, 'rb') as f:
                hash = hashlib.sha1(f.read())
                return hash.digest()
        return None

    # markl as removed
    def remove(self):
        self.size = None
        self.mtime = None
        self.hash = None
        self.type = ModifiedType.REMOVED

    # update size, modified timestamp and hash (if enabled)
    def modified(self, size, mtime):
        if self.size!=size or self.mtime!=mtime:
            self.type = ModifiedType.MODIFIED
            self.size = size
            self.mtime = mtime
        hash = self.hash_file()
        if hash!=self.hash:
            self.hash = hash
            self.type = ModifiedType.MODIFIED
        return self.type

    # update file information
    def update(self):
        if not path.exists(self.file) or not path.isfile(self.file):
            self.remove()
            return
        stat = os.stat(self.file)
        return self.modified(stat.st_size, stat.st_mtime)

    def _todict(self):
        dict = {'file': self.file, 'size': self.size, 'mtime': self.mtime}
        if hash!=None:
            dict['hash'] = hash
        return dict

class FileCollector:

    STORE_PATH = PathType.RELATIVE_PATH

    def __init__(self, database_file, config_file, verbose=False):
        self.verbose = verbose
        self.config_file = config_file
        self.database_file = database_file
        self.database = None
        self.output_files = None
        self.includes = []
        self.defines = {}
        self.filters = { 'include': [], 'exclude': [] }

    @property
    def modified(self):
        return self._modified

    def normalize_path(self, pathname=None):
        if pathname==None:
            pathname=self
        if FileCollector.STORE_PATH==PathType.ABS_PATH:
            return path.abspath(pathname)
        if FileCollector.STORE_PATH==PathType.REAL_PATH:
            return path.abspath(pathname)
        return path.normpath(pathname)

    def prepend_dir(dir, file):
        if dir and not path.isabs(file):
            file = path.join(dir, file)
        return FileCollector.normalize_path(file)

    # parse args.define and add preprocessor defines
    def parse_defines(self, args_define):
        self.defines = {}
        for define in args_define:
            if '=' not in define:
                self.defines[define] = '1'
            else:
                list = define.split('=', 1)
                val = list[1]
                if len(val)>=4 and val.startswith('\\"') and val.endswith('\\"'):
                    val = val[1:-2] + '"'
                self.defines[list[0]] = val

    # add include path
    def add_include(self, dir):
        dir = self.normalize_path(dir)
        if dir not in self.includes:
            if self.verbose:
                print('add include path: %s' % dir)
            self.includes.append(dir)

    # add all files from dir with the given extensions
    def add_dir(self, dir, extensions):
        dir = self.normalize_path(dir)
        if not path.isdir(dir):
            raise RuntimeError('not a directory: %s' % dir)
        for root, subdirs, files in os.walk(dir):
            if self.check_filters(root, True)==FilterType.INCLUDE:
                for file in files:
                    for ext in extensions:
                        if file.endswith(ext):
                            self.add_file(path.join(root, file))

    # add single file
    def add_file(self, file_path):
        file_path = self.normalize_path(file_path)
        if not path.isfile(file_path):
            raise RuntimeError('not a file: %s' % file_path)
        if self.check_filters(file_path, False)==FilterType.INCLUDE:
            if file_path in self.files:
                file = self.files[file_path]
                if file.update()==ModifiedType.UNMODIFIED:
                    if self.verbose:
                        print('unmodified file: %s' % file.file)
                else:
                    print('modified file: %s' % file.file)
            else:
                file = File(file_path)
                file.update()
                file.type = ModifiedType.NEW
                self._modified = True
                self.files[file.file] = file
                if self.verbose:
                    print('new file: %s' % file.file)
        else:
            if file_path in self.database:
                if self.verbose:
                    print('file removed: %s' % file_path)
                self.files[file_path].remove()
                self._modified = True

    @property
    def files(self):
        return self.database['files']

    @property
    def output(self) -> OutputFiles:
        return self.output_files

    # read database
    def read_database(self):
        self._modified = False
        self.database = {
            'files': {},
            'includes': [],
            'defines': {},
            'filters': {},
            'output_files': {}
        }
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
                    files = self.files
                    for item in database['files']:
                        hash = None
                        if hash in item and File.COMPARE==CompareType.HASH:
                            hash = item['hash']
                        file = File(item['file'], item['size'], item['mtime'], hash)
                        if file.update()!=ModifiedType.UNMODIFIED:
                            self._modified = True
                        files[file.file] = file

                    self.database.update({
                        'includes': database['includes'],
                        'defines': database['defines'],
                        'filters': database['filters'],
                        'output_files': database['output_files']
                    })
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
            'files': {},
            'includes': self.includes,
            'defines': self.defines,
            'filters': self.filters,
            'output_files': self.output_files._todict()
        }
        for pathname, file in database['files']:
            self.files[pathname] = file._todict()
        with open(self.database_file, 'wt') as f:
            f.write(json.dumps(database))

    # add normalized output files
    def add_output_files(self, output_declare, output_define, output_static):
        self.output_files = OutputFiles(output_declare, output_define, output_static)

    # check database for modifications
    def check_database(self):
        if self.filters!=self.database['filters']:
            if self.verbose:
                print('filters have been modified')
            self.modified = True
        if self.includes!=self.database['includes']:
            if self.verbose:
                print('includes have been modified')
            self.modified = True
        if self.output_files._todict()!=self.database['output_files']:
            if self.verbose:
                print('output files have been modified')
            self.modified = True

    # add file or directory to the source exclude filter
    def add_src_filter_include(self, dir, base_path = None):
        if base_path:
            dir = path.join(base_path, dir)
        self.filters['include'].append(self.normalize_path(dir))

    # add file or directory to the source include filter
    def add_src_filter_exclude(self, dir, base_path = None):
        if base_path:
            dir = path.join(base_path , dir)
        self.filters['exclude'].append(self.normalize_path(dir))

    def normalize_filter_path(self, filter_path):
        if path.basename(filter_path)=='*':
            return path.join(path.dirname(filter_path), '.')
        # filter_path = filter_path.rstrip('/\\')
        # if filter_path[-1]!='*':
        #     filter_path = path.join(filter_path, '.')
        return filter_path

    # check if a file or directory matches the source filter
    def check_filters(self, path, is_dir):
        debug = False
        if is_dir:
            path = os.path.join(path, '.')
        filter = FilterType.NO_MATCH
        for filter_path in self.filters['include']:
            if not is_dir and filter_path.endswith(os.sep + '.'):
                continue
            if is_dir:
                filter_path = self.normalize_filter_path(filter_path)
            if debug:
                print('include %s=%s' % (filter_path, fnmatch.fnmatch(filter_path, filter_path)))
            if fnmatch.fnmatch(filter_path, filter_path):
                filter = FilterType.INCLUDE
                break
        for filter_path in self.filters['exclude']:
            if not is_dir and filter_path.endswith(os.sep + '.'):
                continue
            if is_dir:
                filter_path = self.normalize_filter_path(filter_path)
            if debug:
                print('exclude %s=%s' % (filter_path, fnmatch.fnmatch(path, filter_path)))
            if fnmatch.fnmatch(path, filter_path):
                filter = FilterType.EXCLUDE
                break
        if debug:
            print('filter=%s is_dir=%s path=%s' % (filter, is_dir, path))
        return filter
