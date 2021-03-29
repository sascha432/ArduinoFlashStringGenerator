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

//
// How to use "FLASH_STRING_GENERATOR_AUTO_INIT"
//
// To define a new PROGMEM string without recreating the flash string database, add
// the FLASH_STRING_GENERATOR_AUTO_INIT macro to your file and use PROGMEM_STRING_DEF
// inside. After adding the string to the database, replace PROGMEM_STRING_DEF with
// AUTO_STRING_DEF. The scanner will automatically update any changes and count the
// usage correctly. Unused strings won't be created and conflicts of definitions with
// different values will show as well
//
// FLASH_STRING_GENERATOR_AUTO_INIT(
//     AUTO_STRING_DEF(ping_monitor_response, "%d bytes from %s: icmp_seq=%d ttl=%d time=%ld ms")
//     AUTO_STRING_DEF(ping_monitor_end_response, "Total answer from %s sent %d recevied %d time %ld ms")
// );

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

#ifndef AUTO_STRING_DEF
#define AUTO_STRING_DEF(...)
#endif
#ifndef FLASH_STRING_GENERATOR_AUTO_INIT
#define FLASH_STRING_GENERATOR_AUTO_INIT(...)
#endif
#endif

#include "spgm_auto_strings.h"
