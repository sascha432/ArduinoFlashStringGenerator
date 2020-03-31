#
# Author: sascha_lammers@gmx.de
#

import os.path
import json
import time
import sys
import fnmatch

class FileCollector:

    def __init__(self, database = None):
        self.database = database
        self.results = {}
        self.is_modified = False
        self.read_database()
        self.filter = { 'include': [], 'exclude': [] }

    # add all files from dir with the given extensions
    def add_dir(self, dir, extensions):
        dir = os.path.realpath(dir)
        if not os.path.isdir(dir):
            raise OSError(dir + ': Not a directory')
        for root, subdirs, files in os.walk(dir):
            if self.check_filter(root, True):
                for file in files:
                    for ext in extensions:
                        if file.endswith(ext):
                            self.add_file(root + os.path.sep + file)

    # add single file
    def add_file(self, file):
        file = os.path.realpath(file)
        if not os.path.isfile(file):
            raise OSError(file + ': File not found')
        if self.check_filter(file, False):
            stat = os.stat(file)
            state = ''
            try:
                if file in self.prev_db.keys():
                    item = self.prev_db[file]
                    if item['size']!=stat.st_size or item['mtime']!=stat.st_mtime:
                        self.is_modified = True
                        state = '*'
                del self.prev_db[file]
            except:
                self.is_modified = True
                state = '+'

            self.results[file] = { 'mtime': int(stat.st_mtime), 'size': stat.st_size, 'state': state }

    # return string for state
    def long_state(self, file):
        state = file['state']
        if state=='+':
            return 'New'
        elif state=='-':
            return 'Removed'
        elif state=='*':
            return 'Modified'
        return 'Not modified'

    # returns true if the list of files or the files itself have been changed
    def modified(self):
        if len(self.prev_db)!=0 or self.database==None:
            return True
        return self.is_modified

    # return files
    def list(self):
        for file in self.prev_db:
            self.results[file] = self.prev_db[file]
            self.results[file]['state'] = '-'
        return self.results

    # read database
    def read_database(self):
        self.prev_db = {}
        if self.database:
            try:
                with open(self.database, 'rt') as file:
                    self.prev_db = json.loads(file.read())
                self.is_modified = False
            except Exception as e:
                pass
        else:
            self.is_modified = True

    # write database
    def write_database(self):
        if self.database:
            try:
                results = dict(self.results)
                removed = []
                for file in results:
                    if results[file]['state']=='-':
                        removed.append(file)
                    else:
                        del results[file]['state']
                for file in removed:
                    del results[file]
                with open(self.database, 'wt') as file:
                    file.write(json.dumps(results))
            except:
                raise OSError(self.database + ": Cannot write database")

    # add file or directory to the source exclude filter
    def add_src_filter_include(self, dir, base_path = None):
        if base_path!=None:
            dir = os.path.realpath(base_path + os.sep + dir)
        self.filter['include'].append(dir)

    # add file or directory to the source include filter
    def add_src_filter_exclude(self, dir, base_path = None):
        if base_path!=None:
            dir = os.path.realpath(base_path + os.sep + dir)
        self.filter['exclude'].append(dir)

    # check if a file or directory matches the source filter
    def check_filter(self, path, is_dir):
        verbose = False
        if is_dir:
            path = path.rstrip('/\\') + os.sep + '.'
        include = 0
        if verbose:
            print("CHECK_FILTER " + path + " is_dir: " + str(is_dir))
        for filter in self.filter['include']:
            if is_dir:
                filter = filter.rstrip('/\\')
                if filter[-1]!='*':
                    filter = filter + os.sep + '.'
            if verbose:
                print(path + ' include ' + filter)
            if fnmatch.fnmatch(path, filter):
                include = 1
                if verbose:
                    print("INCLUDE")
                break
        for filter in self.filter['exclude']:
            if is_dir:
                filter = filter.rstrip('/\\')
                if filter[-1]!='*':
                    filter = filter + os.sep + '.'
            if verbose:
                print(path + ' exclude ' + filter)
            if fnmatch.fnmatch(path, filter):
                include = -1
                if verbose:
                    print("EXCLUDE")
                break
        if verbose and include==0:
            print("NO MATCH")
        if include==1:
            return True
        return False

    def get_filter(self):
        return self.filter