# FlashString Generator for Ardunio with internationalization and localization

This tool can generate PROGMEM strings from source code and a database with support for translations. It is based on [pcpp](https://pypi.org/project/pcpp/), a pure python C preprocessor.

Instead of writing `PSTR("This is my text!")`, `SPGM(This_is_my_text_)` or `SPGM(This_is_my_text_, "This is my text!"))` is being used. Multiple languages are supported, for example `SPGM(hello_world, "Hello World!", fr_FR: "Bonjour le monde!", de_DE: "Hallo Welt!")`. All strings/translations can be defined directly inside the source code, a centrelized header file or the JSON database file. The location of definitions and usage is stored as well, to quickly find it in the source code.

## Change Log

Version 0.1.x is now integrated into for PlatformIO Core

[Change Log v0.1.1](CHANGELOG.md)

## Requirements

- PlatformIO Core 5.x (testd with version 5.1.0)
- Python C Preprocessor, pcpp (tested with version 1.22)

## Installation

PlatformIO Core can be installed with

```bash
pip install platformio
```
or the entire [PlatformIO IDE](https://platformio.org/platformio-ide)

### Getting the requirements for PIO

To install pcpp, run

```bash
pio run -t spgm_install_requirements
```


### platformio.ini

```ini
[env]
lib_deps = ArduinoFlashStringGenerator

extra_scripts =
    pre:scripts/spgm_extra_script.py
    post:scripts/post_extra_script.py
```

The configuration options can found in this `platformio.ini`. All variables start with `custom_spgm_generator.`

### Required include directories

Additional include_dirs have to be defined manually. PlatformIO does not provide the include_dirs for the compiler.

Add all include directories to `custom_spgm_generator.include_dirs`

Getting a list for gcc

```bash
$ echo "" | c:\users/sascha\.platformio/packages/toolchain-atmelavr/bin/avr-gcc.exe -E -v -x c++ - -

[...]
#include "..." search starts here:
#include <...> search starts here:
 .platformio\packages\toolchain-atmelavr\bin\../lib/gcc/avr/5.4.0/include
 .platformio\packages\toolchain-atmelavr\bin\../lib/gcc/avr/5.4.0/include-fixed
 .platformio\packages\toolchain-atmelavr\bin\../lib/gcc/avr/5.4.0/../../../../avr/include
End of search list.
[...]

$ echo "" | .platformio/packages/toolchain-xtensa@2.40802.200502/bin/xtensa-lx106-elf-g++.exe -E -v -x c++ -

[...]
include "..." search starts here:
#include <...> search starts here:
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2/xtensa-lx106-elf
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2/backward
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/include
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/include-fixed
 .platformio\packages\toolchain-xtensa@2.40802.200502\bin\../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include
 [...]

```


### Testing the setup

After a successful setup, the `spgm_*` targets will show up in the list.

```bash
$ pio run --list-targets

Environment    Group     Name                       Title                        Description
-------------  --------  -------------------------  ---------------------------  -----------------------------------------------------
example        Advanced  compiledb                  Compilation Database         Generate compilation database `compile_commands.json`
example        Custom    spgm_build                 build spgm strings
example        Custom    spgm_export_all            export entire spgm database  export all SPGM strings
example        Custom    spgm_export_auto           export spgm auto strings     export SPGM strings marked as auto
example        Custom    spgm_export_config         export spgm config           export SPGM strings marked from config database
example        Custom    spgm_install_requirements  install requirements         install requirements for SPGM generator
example        Generic   clean                      Clean
example        Platform  bootloader                 Burn Bootloader
example        Platform  fuses                      Set Fuses
example        Platform  size                       Program Size                 Calculate program size
example        Platform  upload                     Upload
example        Platform  uploadeep                  Upload EEPROM
```

## Basic Usage

### Syntax

```cpp
// delcare a string
PROGMEM_STRING_DECL(name);

// define a string statically
PROGMEM_STRING_DECL(name, "Default text")

// define a string
AUTO_STRING_DEF(name, "Default text"[, <language>: "<translation>"[, <language1;language2>: "<translation>"], ...])

// get string as const char *
SPGM(name, "Default text"[, <language>: "<translation>"[, <language1;language2>: "<translation>"], ...])

// get string as const _FlashStringHelper *
FSPGM(name, "Default text"[, <language>: "<translation>"[, <language1;language2>: "<translation>"], ...])

```

### Declaring a PROGMEM string

To use a string defined manually in a different source file, the string must be declared inside the source or a header.

```cpp
PROGMEM_STRING_DECL(name);

PROGMEM_STRING_DECL(This_is_my_text);
```

### Defining a PROGMEM string statically

Defining a string manually can be done with `PROGMEM_STRING_DECL`. Translations are not supported, but the tool will create declarations automatically.

```cpp
PROGMEM_STRING_DECL(name, "Default text");

PROGMEM_STRING_DEF(This_is_my_text, "This is my text");
```

### Using a PROGMEM string

Using a PROGMEM string required to include the header file with the declaration. `FlashStringGeneratorAuto.h` declares all strings and provides two macros for easy access.

```cpp
const char *my_string1 = SPGM(name1);
const __FlashStringHelper *my_string2 = FSPGM(name2);
auto my_string3_1 = FSPGM(name3)
auto my_string3_2 = SPGM(name3)
```

If a name is not defined, the tool will automatically create it and add it to the JSON database. It is marked as `auto` and can be modified later. All `auto` items can be exported and added in bulk as well

### Defining a string with (F)SPGM

A string and its translations can be defined with the (F)SPGM macro as well.

```cpp
Serial.print(FSPGM(hello_word, "Hello World!"));
```

If the same name is defined multiple times, a notice is used while running the tool. Redefining different content causes an error.

### Using AUTO_STRING_DEF

This works like `(F)SPGM` and can be used to store strings in a centralized location. Unlike `PROGMEM_STRING_DECL/PROGMEM_STRING_DEF`, strings are declared and defined during compilation.

Different languages are supported as well.

`AUTO_STRING_DEF` required to be wrapped with `FLASH_STRING_GENERATOR_AUTO_INIT()`

```cpp
FLASH_STRING_GENERATOR_AUTO_INIT(
    AUTO_STRING_DEF(ping_monitor_response, "%d bytes from %s: icmp_seq=%d ttl=%d time=%ld ms")
    AUTO_STRING_DEF(ping_monitor_end_response, "Total answer from %s sent %d recevied %d time %ld ms")
    AUTO_STRING_DEF(CURRENCY, "%.2f", en_US: "$%.2f", ch;es;fr;de;it: "%.2fEUR")
);
```

### Modifying automatically created strings

If a name cannot be found, the tool will create a beautified version of it.

For example: This_is_my_text = "This is my text"

Once the project is compiled with spgm_build enabled, the `auto` version is added to the JSON database and can be edited there.

### Internationalization and localization

Besides the "default" translation, it is possible to define different languages. Macros that support translations are `FSPGM`, `SPGM` and `AUTO_STRING_DEF`.

There is no restriction for the language name except that it must be a valid C variable name. Multiple lanuages can be concatenated with `;`.

For example:

`SPGM(CURRENCY, "%.2f", en-US:"$%.2f", en_CA:"CA$%.2f",en_au:"AU$%.2f",de;es;it;fr;ch:"%.2fEUR")`

#### Using a different language

To create PROGMEM strings for a different language, add `custom_spgm_generator.output_language` to the environment.

```ini

[env:my_project]
...

[env:my_project_en]
extends = env:my_project
custom_spgm_generator.output_language = en

[env:my_project_fr]
extends = env:my_project
custom_spgm_generator.output_language = fr*

```

#### Fallback languages

If a translation is missing, the fallback is "default". A list of fallbacks can be added by separating the names with newline or whitespace.

The comparison is case insensitive, `-`and `_` are treated equally and `*` can used as wildcard.

```ini
custom_spgm_generator.output_language--i18n=en-US en-CA en-GB en en-*
```

### More examples

Macros can be used as name or inside the translation.

```cpp
#define TEXT_MACRO "macro"
auto str = SPGM(macro_test, "This is using a " TEXT_MACRO);
```

```cpp
#define VERSION "1.0"
PROGMEM_STRING_DECL(firmware_name, "MyFirmware " VERSION)
```

```cpp
#define MACRO_AS_ID "test_str"
auto str = SPGM(MACRO_AS_ID, "Test String");
```

```cpp
auto str = SPGM(CURRENCY, "%.2f");
```

An example program for Arduino Nano boards is included that uses all options available.

... [example.cpp](src/example.cpp)

#### Translations

The name of the string as key and contains all its information. If the default is defined in the source code, it cannot be changed in this file.

It is recommended to add strings to the source code using (F)SPGM, PROGMEM_STRING_DEF or AUTO_STRING_DEF instead of modifying the JSON database file.

***Warning***: If a string is defined in the source code, the definition in the database file will be updated silently

```json
    "Example1": {                   // name of the string
        "auto": "Example1",         // this is the value the tool assigns automatically
                                    // to modify it, change the key to default. If default
                                    // is defined, auto will be removed
        "use_counter": 2,           // shows how often this id is being used
        "default": "Example #1"
        // translations
        "i18n": {
            "en-US": "Example #1 US version",
            "en-CA": "Example #1 CA version",
            "en-GB": "Example #1 GB version",
            "de-CH": "Beispiel #1",
            "fr-CH": "Exemple #1"
        },
        // source and line number where the string is defined or used
        "locations": "src/example.cpp:9 (PROGMEM_STRING_DEF),src/example.cpp:34 (SPGM)"
    },
    "CURRENCY": {
        "default": "%.2f",
        "i18n": {
            "en-US": "$%.2f",
            "en_CA": "CA$%.2f",
            "en_au": "AU$%.2f",
            "it;fr;es;de": "%.2fEUR",
            // redifinitions must match the previous value
            "bg;de": "%.2fEUR"
        },
        "locations": "src/example.cpp:52 (SPGM),src/example.cpp:53 (SPGM)"
    }
```

### spgm_auto_strings.h

Include this file when using any PROGMEM strings. You can also see where the strings are being used.

```cpp
// src/example.cpp:9 (PROGMEM_STRING_DEF), src/example.cpp:34 (SPGM)
PROGMEM_STRING_DECL(Example1);
// src/example.cpp:10 (PROGMEM_STRING_DEF), src/example.cpp:36 (SPGM)
PROGMEM_STRING_DECL(Example2);
...
```

## Building the example

Adding `custom_spgm_generator.auto_run = always` to the environment will automatically run the SPGM generator during compilation.

Since this slows down the process, it can be deactivated. After every change of the PROGMEM strings, the SPGM generator has to be used once.

Rebuilding/cleaning up the project will execute the SPGM generator during the first compilation using `custom_spgm_generator.auto_run = rebuild`

```bash
pio run -t clean -e example
pio run -e example
```

Set `custom_spgm_generator.auto_run = never` to disable auto run completely and execute the SPGM generator manually by adding the target `spgm_build` to the PIO command.


`pio run -t spgm_build -t buildprog -e example`

or

`pio run -t spgm_build -t upload -e example`

