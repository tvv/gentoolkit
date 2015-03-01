# -*- coding: utf-8 -*-
import sys
import traceback
import logging


class Console(object):
    def __init__(self, locals_dct, globals_dct):
        super(Console, self).__init__()
        self.locals = {"_": None}
        self.locals.update(locals_dct)
        self.globals = globals_dct

    def run(self, cmd):
        fn = '$telnet$'
        result = None
        try:
            out = sys.stdout
            sys.stdout = self
            try:
                code = compile(cmd, fn, 'eval')
                result = eval(code, self.globals, self.locals)
            except:
                try:
                    code = compile(cmd, fn, 'exec')
                    exec code in self.globals, self.locals
                except:
                    return traceback.format_exc()
        finally:
            sys.stdout = out

        self.locals['_'] = result
        if result is not None:
            try:
                return repr(result)
            except:
                logging.exception("Result repr fail")
                return traceback.format_exc()
