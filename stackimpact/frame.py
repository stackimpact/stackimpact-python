
import re

class Frame(object):

    def __init__(self, func_name, filename, lineno):
        self.func_name = func_name
        self.filename = filename
        self.lineno = lineno

        self.cached_str = None

        self._skip = False


    def match(self, other):
        return ((other.func_name is None or other.func_name == self.func_name) and
                (other.filename is None or other.filename == self.filename) and
                (other.lineno is None or other.lineno == self.lineno))


    def __eq__(self, other):
        return  (self.func_name == other.func_name and 
                self.filename == other.filename and 
                self.lineno == other.lineno)

    def __str__(self):
        if not self.cached_str:
            if self.lineno is not None and self.lineno > 0:
                self.cached_str = '{0} ({1}:{2})'.format(self.func_name, self.filename, self.lineno)
            else:
                self.cached_str = '{0} ({1})'.format(self.func_name, self.filename)

        return self.cached_str
