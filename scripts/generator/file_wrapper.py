#
# Author: sascha_lammers@gmx.de
#


# detect compression format by file extension
class FileWrapper(object):
    def __init__(self, file, filename, mode, is_open=True):
        self._file = file
        self._filename = filename
        self._mode = mode
        self._is_open = is_open

    def open(filename, mode):
        if filename.lower().endswith('.xz'):
            module = 'lzma'
        else:
            module = 'builtins'
        module = __import__(module)
        return FileWrapper(getattr(module, 'open')(filename, mode), filename, mode, True)

    def __enter__(self):
        return object.__getattribute__(self, '_file')

    def __exit__(self, type, value, traceback):
        self.close()
        return False

    @property
    def name(self):
        return object.__getattribute__(self, 'name')

    @property
    def mode(self):
        return object.__getattribute__(self, 'mode')

    @property
    def closed(self):
        return object.__getattribute__(self, 'closed')

    def close(self):
        file = object.__getattribute__(self, '_file')
        self._is_open = False
        file.close()

    def __getattribute__(name):
        return object.__getattribute__(FileWrapper, name)

    def __getattribute__(self, name):
        if name=='close':
            return object.__getattribute__(self, 'close')
        file = object.__getattribute__(self, '_file')
        if hasattr(file, name):
            return getattr(file, name)
        if name=='name':
            return object.__getattribute__(self, '_filename')
        if name=='mode':
            return object.__getattribute__(self, '_mode')
        if name=='closed':
            return not object.__getattribute__(self, '_is_open')
        # raise exception
        return object.__getattribute__(file, name)
