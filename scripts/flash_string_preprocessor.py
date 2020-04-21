#
# Author: sascha_lammers@gmx.de
#

import sys
import os
import json
from pcpp.preprocessor import Preprocessor, OutputDirective, Action
from json_schema.json_differ import diff_jsons

class FlashStringPreprocessor(Preprocessor):
    def __init__(self):
        super(FlashStringPreprocessor, self).__init__()
        self.define('PSTR(content) __INTERNAL_USE_PSTR_START(#content,__INTERNAL_USE_PSTR_END)')
        self.define('SPGM(name, ...) __INTERNAL_USE_FLASH_STRING_START(#name,__INTERNAL_USE_FLASH_STRING_END,##__VA_ARGS__,__INTERNAL_USE_FLASH_STRING_END_VA_ARGS)')
        self.define('FSPGM(name, ...) __INTERNAL_USE_FLASH_STRING_START(#name,__INTERNAL_USE_FLASH_STRING_END,##__VA_ARGS__,__INTERNAL_USE_FLASH_STRING_END_VA_ARGS)')
        self.define('PROGMEM_STRING_DEF(name, value) __INTERNAL_DEFINE_FLASH_STRING_START(#name,value,__INTERNAL_DEFINE_FLASH_STRING_END)')
        self.spgm_defined = []
        self.spgm_used = []
        self.pstr = []
        self.annotations = {}
        self.ignore_includes = []
        # self.debugout = sys.stdout

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
            elif tok.type!='CPP_LESS' and tok.type!='CPP_GREATER':
                str += tok.value
        return str

    def on_directive_handle(self,directive,toks,ifpassthru,precedingtoks):
        if directive.value=='define' or directive.value=='undef':
            if toks[0].type=='CPP_ID':
                if toks[0].value in ['SPGM', 'FSPGM', 'PROGMEM_STRING_DEF']:
                    raise OutputDirective(Action.IgnoreAndPassThrough)
        elif directive.value=='include':
            for path in self.path:
                include_file = os.path.realpath(path + os.sep + self.tokens_to_string(toks))
                if include_file in self.ignore_includes:
                    raise OutputDirective(Action.IgnoreAndPassThrough)
        return super(FlashStringPreprocessor, self).on_directive_handle(directive,toks,ifpassthru,precedingtoks)

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
        lastlineno = 0
        lastsource = None
        done = False
        blanklines = 0
        internal_define = None
        while not done:
            emitlinedirective = False
            toks = []
            all_ws = True
            # Accumulate a line
            while not done:
                tok = self.token()
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
                if lastsource is None:
                    if toks[0].source is not None:
                        emitlinedirective = True
                    lastsource = toks[0].source
                elif lastsource != toks[0].source:
                    emitlinedirective = True
                    lastsource = toks[0].source
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
                newlinesneeded = toks[0].lineno - lastlineno - 1
                if newlinesneeded > 6 and self.line_directive is not None:
                    emitlinedirective = True
                else:
                    while newlinesneeded > 0:
                        # oh.write('\n')
                        newlinesneeded -= 1
            lastlineno = toks[0].lineno
            # Account for those newlines in a multiline comment
            if toks[0].type == self.t_COMMENT1:
                lastlineno += toks[0].value.count('\n')
            # if emitlinedirective and self.line_directive is not None:
            #     oh.write(self.line_directive + ' ' + str(lastlineno) + ('' if lastsource is None else (' "' + lastsource + '"' )) + '\n')
            blanklines = 0
            #print toks[0].lineno,
            for tok in toks:
                if tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_FLASH_STRING_START':
                    internal_define = 'define_spgm'
                    self.last_spgm = ''
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_FLASH_STRING_END':
                    internal_define = 'define_spgm_va_args'
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_FLASH_STRING_END_VA_ARGS':
                    internal_define = None
                if internal_define=='define_spgm' and tok.type=='CPP_STRING':
                    self.last_spgm = tok.value[1:-1]
                    self.add_spgm(self.last_spgm, lastlineno, lastsource)
                elif internal_define=='define_spgm_va_args' and tok.type=='CPP_STRING':
                    self.add_annotation(self.last_spgm, tok.value, lastlineno, lastsource)

                if tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_PSTR_START':
                    internal_define = 'pstr'
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_USE_PSTR_END':
                    internal_define = None
                if internal_define=='pstr' and tok.type=='CPP_STRING':
                    self.add_pstr(tok.value[1:-1], lastlineno, lastsource)

                if tok.type=='CPP_ID' and tok.value=='__INTERNAL_DEFINE_FLASH_STRING_START':
                    internal_define = 'spgm'
                    spgm_define = {'value': ''}
                elif tok.type=='CPP_ID' and tok.value=='__INTERNAL_DEFINE_FLASH_STRING_END':
                    internal_define = None
                    self.add_spgm_define(spgm_define, lastlineno, lastsource)
                if internal_define=='spgm' and tok.type=='CPP_STRING':
                    if not 'name' in spgm_define.keys():
                        spgm_define['name'] = tok.value[1:-1]
                    else:
                        spgm_define['value'] = spgm_define['value'] + tok.value[1:-1]


    def add_pstr(self, value, line, file):
        if value.startswith('\\"'):
            self.pstr.append({ 'value': bytes(value[2:-2], 'utf-8').decode('unicode_escape'), 'file': file, 'line': line })

    def add_spgm(self, value, line, file):
        self.spgm_used.append({ 'value': value, 'file': file, 'line': line })

    def add_spgm_define(self, define, line, file):
        self.spgm_defined.append({ 'name': define['name'], 'value': define['value'], 'file': file, 'line': line })

    def parse_annotation(self, annotation):
        if annotation.startswith('{') and annotation.endswith('}'):
            tmp = eval(annotation)
            if isinstance(tmp, dict):
                return tmp
            raise RuntimeError("Invalid annotation: '" + annotation + "'")
        else:
            return {'*': annotation}

    def add_annotation(self, define, annotation, line, file):
        new_annotation = self.parse_annotation(annotation[1:-1])
        if define in self.annotations.keys():
            item = self.annotations[define]
            diff = diff_jsons(json.dumps(item['annotation']), json.dumps(new_annotation))
            if diff==False:
                raise RuntimeError('Previous definition for ' + define + ' has changed\n' + item['file'] + ':' + str(item['line']) + ' ' + str(item['annotation']) + '\n' + file + ':' + str(line) + ' ' + str(new_annotation))
        else:
            self.annotations[define] = {'annotation': new_annotation, 'file': file, 'line': line}

    def get_used(self):
        return self.spgm_used

    def get_defined(self):
        return self.spgm_defined

    def get_pstr(self):
        return self.pstr

    def get_annotations(self):
        return self.annotations
