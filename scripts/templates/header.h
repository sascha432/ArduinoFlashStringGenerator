#pragma once
#include <avr/pgmspace.h>
#ifndef PROGMEM_STRING_DECL
#define PROGMEM_STRING_DECL(name)               extern const char _shared_progmem_string_##name[] PROGMEM;
#define PROGMEM_STRING_DEF(name, value)         const char _shared_progmem_string_##name[] PROGMEM = { value };
#endif
#ifndef SPGM
#define SPGM(name, ...)                         _shared_progmem_string_##name
#define FSPGM(name, ...)                        reinterpret_cast<const __FlashStringHelper *>(SPGM(name))
#endif
