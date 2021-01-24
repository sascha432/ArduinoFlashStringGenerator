#
# Author: sascha_lammers@gmx.de
#

import sys
import os
from os import path
from . import Item
try:
    from pcpp.preprocessor import Preprocessor, OutputDirective, Action
except Exception as e:
    print("-"*76)
    print("Cannot import pcpp")
    print("Exception: %s" % e)
    print("Path: %s" % sys.path)
    sys.exit(1)

class FlashStringPreprocessor(Preprocessor):
    def __init__(self):
        super(FlashStringPreprocessor, self).__init__()
        self.define("FLASH_STRINGS_AUTO_INIT 1")
        self.define("AUTO_INIT_SPGM(name, ...) __INTERNAL_AUTOINIT_FLASH_STRING_START(#name,__VA_ARGS__,__INTERNAL_AUTOINIT_FLASH_STRING_END)")
        self.define("SPGM(name, ...) __INTERNAL_SPGM_FLASH_STRING_START(#name,__VA_ARGS__,__INTERNAL_SPGM_FLASH_STRING_END)")
        self.define("FSPGM(name, ...) __INTERNAL_SPGM_FLASH_STRING_START(#name,__VA_ARGS__,__INTERNAL_SPGM_FLASH_STRING_END)")
        self.define("PROGMEM_STRING_DEF(name, value) __INTERNAL_DEFINE_FLASH_STRING_START(#name,value,__INTERNAL_DEFINE_FLASH_STRING_END)")
        self.ignore_includes = []
        # self.debugout = sys.stdout
        self._items = []

    def add_ignore_include(self, include):
        self.ignore_includes.append(include)

    # def on_include_not_found(self,is_system_include,curdir,includepath):
    #     print('******** on_include_not_found')
    #     print(is_system_include)
    #     print(curdir)
    #     print(includepath)
    #     return super(FlashStringPreprocessor, self).on_include_not_found(is_system_include,curdir,includepath)

    # def on_unknown_macro_in_defined_expr(self,tok):
    #     print('******** on_unknown_macro_in_defined_expr')
    #     print(tok)
    #     return super(FlashStringPreprocessor, self).on_unknown_macro_in_defined_expr(tok)

    # def on_unknown_macro_in_expr(self,tok):
    #     print('********** on_unknown_macro_in_expr')
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
            if toks[0].type=='CPP_ID' and toks[0].value in ['SPGM', 'FSPGM', 'PROGMEM_STRING_DEF', 'FLASH_STRING_GENERATOR_AUTO_INIT', 'AUTO_INIT_SPGM']:
                raise OutputDirective(Action.IgnoreAndPassThrough)
        elif directive.value=='include':
            for path in self.path:
                if not os.path.isabs(path):
                    path = os.path.abspath(os.path.join(path, self.tokens_to_string(toks)))
                if os.path.isfile(path):
                    if path in self.ignore_includes:
                        raise OutputDirective(Action.IgnoreAndPassThrough)
        return super(FlashStringPreprocessor, self).on_directive_handle(directive, toks, ifpassthru, precedingtoks)

    # def on_directive_unknown(self,directive,toks,ifpassthru,precedingtoks):
    #     print('******** on_directive_unknown')
    #     print(directive)
    #     print(toks)
    #     print(ifpassthru)
    #     print(precedingtoks)
    #     return super(FlashStringPreprocessor, self).on_directive_unknown(directive,toks,ifpassthru,precedingtoks)

    # def on_potential_include_guard(self,macro):
    #     print('******** on_potential_include_guard')
    #     print(macro)
    #     return super(FlashStringPreprocessor, self).on_potential_include_guard(macro)

    def on_error(self, file, line, msg):
        # print(file + ':' + str(line) + ': ' + msg)
        # sys.exit(1)
        return super(FlashStringPreprocessor, self).on_error(file, line, msg)

    def find_strings(self, oh=sys.stdout):
        self.lineno = 0
        self.source = None
        done = False
        blanklines = 0
        item = None
        while not done:
            emitlinedirective = False
            toks = []
            all_ws = True
            # Accumulate a line
            while not done:
                try:
                    tok = self.token()
                except Exception as e:
                    raise RuntimeError('exception before %s:%u: %s' % (self.source, self.lineno, e))
                if not tok:
                    done = True
                    break

                toks.append(tok)
                if not tok.value or tok.value.startswith('\n') or tok.value.startswith('\r\n'):
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
                if self.source is None:
                    if toks[0].source is not None:
                        emitlinedirective = True
                    self.source = toks[0].source
                elif self.source != toks[0].source:
                    emitlinedirective = True
                    self.source = toks[0].source
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
                newlinesneeded = toks[0].lineno - self.lineno - 1
                if newlinesneeded > 6 and self.line_directive is not None:
                    emitlinedirective = True
                else:
                    while newlinesneeded > 0:
                        # oh.write('\n')
                        newlinesneeded -= 1
            self.lineno = toks[0].lineno
            # Account for those newlines in a multiline comment
            if toks[0].type == self.t_COMMENT1:
                self.lineno += toks[0].value.count('\n')
            # if emitlinedirective and self.line_directive is not None:
            #     oh.write(self.line_directive + ' ' + str(self.lineno) + ('' if self.source is None else (' "' + self.source + '"' )) + '\n')
            blanklines = 0
            #print toks[0].lineno,
            for tok in toks:
                if tok.type=='CPP_ID' and tok.value.startswith('__INTERNAL_') and tok.value.endswith('_FLASH_STRING_START'):
                    parts = tok.value.split('_', 4)
                    type = parts[3]=='AUTOINIT' and 'AUTO_INIT' or parts[3]
                    item = Item(type, self.source, self.lineno, item=item)
                elif tok.type=='CPP_ID' and tok.value in('__INTERNAL_SPGM_FLASH_STRING_END','__INTERNAL_DEFINE_FLASH_STRING_END', '__INTERNAL_AUTOINIT_FLASH_STRING_END'):
                    item = self.add_item(item)
                elif item!=None:
                    if tok.type=='CPP_STRING':
                        item.append_value_buffer(tok.value[1:-1])
                    elif (tok.type=='CPP_DOT' and tok.value==',') or tok.type=='CPP_COMMA':
                        item.push_value()
                    elif (tok.type=='CPP_DOT' and tok.value==':') or tok.type=='CPP_COLON':
                        # assign lanuage
                        item.push_value()
                    elif tok.type in ['CPP_ID', 'CPP_MINUS', 'CPP_DOT', 'CPP_SEMICOLON']:
                        item.append_value_buffer(tok.value)
                    elif tok.type=='CPP_STRING':
                        item.append_value_buffer(tok.value[1:-1])


                if Item.DebugType.TOKEN in Item.DEBUG and item:
                    print("value=%s type=%s %s" % (tok.value, tok.type, item))

    def add_item(self, item):
        # push any text from buffer that is left
        if item.has_value_buffer:
            item.push_value()
        item.validate()
        item.cleanup()
        self._items.append(item)
        return None

    @property
    def items(self):
        return self._items
