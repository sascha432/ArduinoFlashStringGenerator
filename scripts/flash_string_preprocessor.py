#
# Author: sascha_lammers@gmx.de
#

import sys
import os
from os import path
from pcpp.preprocessor import Preprocessor, OutputDirective, Action

class FlashStringPreprocessor(Preprocessor):
    def __init__(self):
        super(FlashStringPreprocessor, self).__init__()
        self.define("SPGM(name, ...) __INTERNAL_USE_FLASH_STRING_START(#name,__VA_ARGS__,__INTERNAL_USE_FLASH_STRING_END)")
        self.define("FSPGM(name, ...) __INTERNAL_USE_FLASH_STRING_START(#name,__VA_ARGS__,__INTERNAL_USE_FLASH_STRING_END)")
        self.define("PROGMEM_STRING_DEF(name, value) __INTERNAL_DEFINE_FLASH_STRING_START(#name,value,__INTERNAL_DEFINE_FLASH_STRING_END)")
        self.spgm_defined = []
        self.spgm_used = []
        self.ignore_includes = []
        # self.debugout = sys.stdout

    def add_ignore_include(self, include):
        self.ignore_includes.append(include)

    # def on_include_not_found(self,is_system_include,curdir,includepath):
    #     print("******** on_include_not_found")
    #     print(is_system_include)
    #     print(curdir)
    #     print(includepath)
    #     return super(FlashStringPreprocessor, self).on_include_not_found(is_system_include,curdir,includepath)

    # def on_unknown_macro_in_defined_expr(self,tok):
    #     print("******** on_unknown_macro_in_defined_expr")
    #     print(tok)
    #     return super(FlashStringPreprocessor, self).on_unknown_macro_in_defined_expr(tok)

    # def on_unknown_macro_in_expr(self,tok):
    #     print("********** on_unknown_macro_in_expr")
    #     print(tok)
    #     return super(FlashStringPreprocessor, self).on_unknown_macro_in_expr(tok)

    def tokens_to_string(self, toks):
        str = ''
        for tok in toks:
            if tok.type=='CPP_STRING':
                str += tok.value[1:-1]
            elif tok.type not in ['CPP_LESS', 'CPP_GREATER']:
                str += tok.value
        return str

    def on_directive_handle(self, directive, toks, ifpassthru, precedingtoks):
        if directive.value=='define' or directive.value=='undef':
            if toks[0].type=='CPP_ID' and toks[0].value in ['SPGM', 'FSPGM', 'PROGMEM_STRING_DEF']:
                raise OutputDirective(Action.IgnoreAndPassThrough)
        elif directive.value=='include':
            for path in self.path:
                #include_file = os.path.realpath(path + os.sep + self.tokens_to_string(toks))
                include_file = os.path.realpath(os.path.join(path, self.tokens_to_string(toks)))
                if os.path.isfile(include_file):
                    if include_file in self.ignore_includes:
                        print("ignore %s" % include_file)
                        raise OutputDirective(Action.IgnoreAndPassThrough)
        return super(FlashStringPreprocessor, self).on_directive_handle(directive,toks,ifpassthru,precedingtoks)

    # def on_directive_unknown(self,directive,toks,ifpassthru,precedingtoks):
    #     print("******** on_directive_unknown")
    #     print(directive)
    #     print(toks)
    #     print(ifpassthru)
    #     print(precedingtoks)
    #     return super(FlashStringPreprocessor, self).on_directive_unknown(directive,toks,ifpassthru,precedingtoks)

    # def on_potential_include_guard(self,macro):
    #     print("******** on_potential_include_guard")
    #     print(macro)
    #     return super(FlashStringPreprocessor, self).on_potential_include_guard(macro)

    def on_error(self, file, line, msg):
        # print(file + ':' + str(line) + ': ' + msg)
        # sys.exit(1)
        return super(FlashStringPreprocessor, self).on_error(file, line, msg)

    def find_strings(self, oh=sys.stdout):
        self.lastlineno = 0
        self.lastsource = None
        done = False
        blanklines = 0
        spgm_args = None
        is_spgm_define = False
        while not done:
            emitlinedirective = False
            toks = []
            all_ws = True
            # Accumulate a line
            while not done:
                try:
                    tok = self.token()
                except Exception as e:
                    raise RuntimeError('exception: %s:%u: %s' % (self.lastsource, self.lastlineno, e))
                if not tok:
                    done = True
                    break
                toks.append(tok)
                if tok.value[0] == '\n':
                    break
                if tok.type not in self.t_WS:
                    all_ws = False
            if not toks:
                break
            if all_ws:
                # Remove preceding whitespace so it becomes just a LF
                if len(toks) > 1:
                    tok = toks[-1]
                    toks = [ tok ]
                blanklines += toks[0].value.count('\n')
                continue
            # The line in toks is not all whitespace
            emitlinedirective = (blanklines > 6) and self.line_directive is not None
            if hasattr(toks[0], 'source'):
                if self.lastsource is None:
                    if toks[0].source is not None:
                        emitlinedirective = True
                    self.lastsource = toks[0].source
                elif self.lastsource != toks[0].source:
                    emitlinedirective = True
                    self.lastsource = toks[0].source
            # Replace consecutive whitespace in output with a single space except at any indent
            first_ws = None
            for n in range(len(toks)-1, -1, -1):
                tok = toks[n]
                if first_ws is None:
                    if tok.type in self.t_SPACE or len(tok.value) == 0:
                        first_ws = n
                else:
                    if tok.type not in self.t_SPACE and len(tok.value) > 0:
                        m = n + 1
                        while m != first_ws:
                            del toks[m]
                            first_ws -= 1
                        first_ws = None
                        if self.compress > 0:
                            # Collapse a token of many whitespace into single
                            if toks[m].value[0] == ' ':
                                toks[m].value = ' '
            if not self.compress > 1 and not emitlinedirective:
                newlinesneeded = toks[0].lineno - self.lastlineno - 1
                if newlinesneeded > 6 and self.line_directive is not None:
                    emitlinedirective = True
                else:
                    while newlinesneeded > 0:
                        # oh.write('\n')
                        newlinesneeded -= 1
            self.lastlineno = toks[0].lineno
            # Account for those newlines in a multiline comment
            if toks[0].type == self.t_COMMENT1:
                self.lastlineno += toks[0].value.count('\n')
            # if emitlinedirective and self.line_directive is not None:
            #     oh.write(self.line_directive + ' ' + str(self.lastlineno) + ('' if self.lastsource is None else (' "' + self.lastsource + '"' )) + '\n')
            blanklines = 0
            #print toks[0].lineno,
            for tok in toks:

                # [F]PSGM

                if tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_FLASH_STRING_START':
                    spgm_args = { 'current': 'default', 'text': '', 'i18n': {}, 'arg_num': 0 }
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_FLASH_STRING_END':
                    self.add_spgm(spgm_args, self.lastlineno, self.lastsource)
                    spgm_args = None
                elif spgm_args!=None:
                    if tok.type=='CPP_STRING':
                        # first argument is the id
                        if spgm_args['arg_num']==0:
                            spgm_args['value'] = tok.value[1:-1]
                            # second argument is "default"
                        elif spgm_args['arg_num']==1:
                            spgm_args['default'] = spgm_args['text'] + tok.value[1:-1]
                        else:
                            # others are translations
                            spgm_args['i18n'][spgm_args['current'].strip()] = spgm_args['text'] + tok.value[1:-1]
                        spgm_args['text'] = spgm_args['text'] + tok.value[1:-1]

                    elif tok.type=='CPP_DOT' and tok.value==',':
                        spgm_args['arg_num'] = spgm_args['arg_num'] + 1
                        if 'value' not in spgm_args:
                            raise RuntimeError('Name/id missing: %s:%u' % (self.lastsource, self.lastlineno))
                        spgm_args['current'] = ''
                        spgm_args['text'] = ''
                    elif tok.type=='CPP_DOT' and tok.value==':':
                        spgm_args['current'] = spgm_args['text']
                        spgm_args['text'] = ''
                    elif tok.type in ['CPP_ID', 'CPP_MINUS', 'CPP_DOT']:
                        spgm_args['text'] = spgm_args['text'] + tok.value
                    elif tok.type=='CPP_STRING':
                        spgm_args['text'] = spgm_args['text'] + tok.value[1:-1]

                # PROGMEM_STRING_DEF

                if tok.type=='CPP_ID' and tok.value=='__INTERNAL_DEFINE_FLASH_STRING_START':
                    is_spgm_define = True
                    spgm_define = {'value': ''}
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_DEFINE_FLASH_STRING_END':
                    is_spgm_define = False
                    self.add_spgm_define(spgm_define, self.lastlineno, self.lastsource)

                if is_spgm_define and tok.type=='CPP_STRING':
                    if not 'name' in spgm_define.keys():
                        spgm_define['name'] = tok.value[1:-1]
                    else:
                        spgm_define['value'] = spgm_define['value'] + tok.value[1:-1]


    def add_spgm(self, values, line, file):
        values['file'] = file;
        values['line'] = line;
        if not values['i18n']:
            del values['i18n']
        del values['current']
        del values['text']
        del values['arg_num']
        self.spgm_used.append(values)

    def add_spgm_define(self, define, line, file):
        self.spgm_defined.append({ 'name': define['name'], 'value': define['value'], 'file': file, 'line': line })

    def get_used(self):
        return self.spgm_used

    def get_defined(self):
        return self.spgm_defined
