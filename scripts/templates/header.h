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

#if FLASH_STRINGS_AUTO_INIT
#define AUTO_STRING_DEF(...)                            AUTO_INIT_SPGM(__VA_ARGS__),
#define FLASH_STRING_GENERATOR_AUTO_INIT(...) \
    static bool __flash_string_generator_auto_init_var = []() { \
        SPGM_P strings[] = { \
            __VA_ARGS__ nullptr \
        };
        return true; \
    }
#else

#define AUTO_STRING_DEF(...)
#define FLASH_STRING_GENERATOR_AUTO_INIT(...)
#endif

#include "spgm_auto_strings.h"
