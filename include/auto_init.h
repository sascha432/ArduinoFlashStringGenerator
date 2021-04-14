// centralized header file
// To define a new PROGMEM string or its translation without using it in the source code, use the AUTO_STRING_DEF macro

#pragma once

#if FLASH_STRINGS_AUTO_INIT
#ifndef AUTO_INIT_SPGM
#error FLASH_STRINGS_AUTO_INIT should not be set
#endif
#else
#ifndef AUTO_STRING_DEF
#define AUTO_STRING_DEF(name, ...) PROGMEM_STRING_DECL(name);
#endif
#endif

#ifdef __cplusplus
extern "C" {
#endif

AUTO_STRING_DEF(AutoInitExample, "test default lang", en_EN: "test en_EN", it_IT: "tests it_IT", fr_FR: "fr_FR")

}