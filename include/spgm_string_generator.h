/**
 * Author: sascha_lammers@gmx.de
 */

#pragma once

#include <avr/pgmspace.h>

#define PROGMEM_STRING_ID(name)                         SPGM_##name

#ifndef PROGMEM_STRING_DECL
#define PROGMEM_STRING_DECL(name)                       extern const char PROGMEM_STRING_ID(name)[] PROGMEM;
#define PROGMEM_STRING_DEF(name, value)                 const char PROGMEM_STRING_ID(name)[] PROGMEM = { value };
#endif

#ifndef SPGM
#ifndef FPSTR
class __FlashStringHelper;
#define FPSTR(pstr_pointer)                             (reinterpret_cast<const __FlashStringHelper *>(pstr_pointer))
#endif
#define SPGM(name, ...)                                 PROGMEM_STRING_ID(name)
#define FSPGM(name, ...)                                FPSTR(SPGM(name))
#define PSPGM(name, ...)                                (PGM_P)(SPGM(name))
#endif

#ifndef AUTO_STRING_DEF
#define AUTO_STRING_DEF(name, ...)                      PROGMEM_STRING_DECL(name);
#endif

#include "spgm_auto_strings.h"
#include "auto_init.h"
