#pragma once

#include <avr/pgmspace.h>

#ifndef PROGMEM_STRING_PREFIX
#define PROGMEM_STRING_PREFIX                   _shared_progmem_string_
#endif

#ifndef PROGMEM_STRING_DECL
#define PROGMEM_STRING_DECL(name)               extern const char PROGMEM_STRING_PREFIX##name[] PROGMEM;
#define PROGMEM_STRING_DEF(name, value)         const char PROGMEM_STRING_PREFIX##name[] PROGMEM = { value };
#endif

#ifndef SPGM
#define SPGM(name)                              PROGMEM_STRING_PREFIX##name
#define FSPGM(name)                             reinterpret_cast<const __FlashStringHelper *>(SPGM(name))
#endif
