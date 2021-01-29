# FlashString Generator for Ardunio with internationalization and localization

This tool can generate PROGMEM strings from source code. It is based on [pcpp](https://pypi.org/project/pcpp/), a pure python C preprocessor.

Instead of writing `PSTR("This is my text!")`, `SPGM(This_is_my_text_)` or `SPGM(This_is_my_text_, "This is my text!"))` is being used. Running the tool will check all source code and generate the defined PROGMEM strings. Multiple languages are supported, for example `SPGM(hello_world, "Hello World!", fr_FR: "Bonjour le monde!", de_DE: "Hallo Welt!")`. All strings/translations can be defined directly inside the source code or a JSON file. The location of definitions and usage is stored as well.

## Change Log

[Change Log v0.0.4](CHANGELOG.md)

WARNING! file is not up to date and there were major changes. check examples in platform.ini

[Change Log v0.1.0](CHANGELOG.md)

## Requirements

- pcpp (tested with 1.22)

Install pcpp in a directory that is in the platformio path or use PIO to install it

```bash
pio run -t spgm_generator_install_requirements
```

## Basic usage

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
const char *my_string = SPGM(name);
const __FlashStringHelper *my_string = FSPGM(name);
```

If a name is not defined, the tool will automatically create it and add it to the JSON database. It is marked as automatically created and can be modified later.

Defining a string in `(F)SPGM` can be done as well.

```cpp
Serial.print(FSPGM(hello_word, "Hello World!"));
```

If the same name is defined multiple times, a notice is used while running the tool. Redefining different content causes an error.

### Using AUTO_STRING_DEF

This works like `(F)SPGM` and can be used to store strings in a centralized location. Unlike `PROGMEM_STRING_DECL/PROGMEM_STRING_DEF`, strings are not declared or defined until the tool has been executed. Different languages are supported as well.

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

After running the tool, it creates an entry in the JSON database where it can be changed and adds a copy to FlashStringGeneratorAuto.auto

Strings that are not being used anymore are removed from the source and declaration, but kept in `FlashStringGeneratorAuto.json`

### Internationalization and localization

Besides the "default" translation, it is possible to define different languages. Macros that support translations are `FSPGM`, `SPGM` and `AUTO_STRING_DEF`.

There is no restriction for the language name except it must be a valid C variable name. Multiple lanuages can be concatenated with `;`.

For example:

`SPGM(CURRENCY, "%.2f", en-US:"$%.2f", en_CA:"CA$%.2f",en_au:"AU$%.2f",de;es;it;fr;ch:"%.2fEUR")`

#### Using a different language

To create PROGMEM strings for a different language, use the argument `--i18n`

`--i18n=en-US`
`--i18n=en-CA`
`--i18n=en-GB`
`--i18n=fr-CH`
`--i18n=de-CH`
`--i18n=it`

If a translation is missing, the default fallback is "default". A list of fallbacks can be specified by using a comma separated list as argument.

The comparison is non-case sensitive, `-`and `_` are treated equally and `*` can used as wildcard.

`--i18n=en-US,en,en-CA,en-GB,en-*,default`

### More examples

```cppp
#define TEXT_MACRO "macro"
auto str = SPGM(macro_test, "This is using a " TEXT_MACRO);
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

## Using the standalone version

For this example, you can run

```bash
python .\scripts\flashstringgen.py -d ./src --src-filter-include * --src-filter--exclude ignore_me.cpp --output-dir=./src/generated
```

It will scan all source files in `./src` and its sub directories, except `ignore_me.cpp` and create the files in `./src/generated`. The default file extension for source files is `.c`, `.cpp`and `.ino`.

### FlashStringGeneratorAuto.json

This file contains the database of all strings.

#### Configuration options

These are stored under the key `__FLASH_STRING_GENERATOR_CONFIG__`. When the file is created the first time, all default options are added.

#### Translations

The name of the string as key and contains all its information. If the default is defined in the source code, it cannot be changed in this file.

It is recommended to add strings to the source code using (F)SPGM, PROGMEM_STRING_DEF or AUTO_STRING_DEF instead of modifying this file.

***Warning***: If a string is defined in the source code, the definition in the file will be updated silently

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

### FlashStringGeneratorAuto.h

Include this file when using any PROGMEM strings. You can also see where the strings are being used.

```cpp
// src/example.cpp:9 (PROGMEM_STRING_DEF), src/example.cpp:34 (SPGM)
PROGMEM_STRING_DECL(Example1);
// src/example.cpp:10 (PROGMEM_STRING_DEF), src/example.cpp:36 (SPGM)
PROGMEM_STRING_DECL(Example2);
...
```

## Using PlatformIO and extra_scripts

If using PlatformIO, you can use extra_scripts to provide a target that creates the PROGMEM strings.

Simply add `extra_scripts = scripts/extra_script.py` to your platformio.ini and execute it with `pio run -t buildspgm` or `pio run -t rebuildspgm`.

Using external libraries with translations requires to add the source directory and source filter manually.

### include_path

Additional include_paths have to be defined manually. Platformio does not provide the include_path for the compiler.

Getting a list for gcc and g++

```bash
# .platformio/packages/toolchain-atmelavr/bin/avr-gcc.exe -E -v -

[...]
#include "..." search starts here:
#include <...> search starts here:
 ~/.platformio/packages/toolchain-atmelavr/bin/../lib/gcc/avr/5.4.0/include
 ~/.platformio/packages/toolchain-atmelavr/bin/../lib/gcc/avr/5.4.0/include-fixed
 ~/.platformio/packages/toolchain-atmelavr/bin/../lib/gcc/avr/5.4.0/../../../../avr/include
End of search list.
[...]

.platformio/packages/toolchain-xtensa@2.40802.200502/bin/xtensa-lx106-elf-g++.exe -E -v -x c++ -

[...]
#include "..." search starts here:
#include <...> search starts here:
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2/xtensa-lx106-elf
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include/c++/4.8.2/backward
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/include
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/include-fixed
 ~/.platformio/packages/toolchain-xtensa@2.40802.200502/bin/../lib/gcc/xtensa-lx106-elf/4.8.2/../../../../xtensa-lx106-elf/include
End of search list.
[...]

```

### platformio.ini example

This is an example that uses external libraries with translations and customizations.

```ini
extra_scripts =
    ../ArduinoFlashStringGenerator/scripts/extra_script.py

; additonal include directories that are processed by sub parsers
custom_spgm_generator.include_path =
    ${PROJECT_DIR}/lib/*/include/*
    ${platformio.packages_dir}/toolchain-xtensa@2.40802.200502/xtensa-lx106-elf/include/c++/4.8.2/xtensa-lx106-elf
    ${platformio.packages_dir}/toolchain-xtensa@2.40802.200502/lib/gcc/xtensa-lx106-elf/4.8.2/include
    ${platformio.packages_dir}/toolchain-xtensa@2.40802.200502/xtensa-lx106-elf/include/c++/4.8.2
    ${platformio.packages_dir}/toolchain-xtensa@2.40802.200502/xtensa-lx106-elf/include

; ignore these files when included in any source
custom_spgm_generator.ignore_includes =
    ${platformio.packages_dir}/framework-arduinoespressif8266/libraries/ESP8266mDNS/src/LEAmDNS.h
    ${platformio.packages_dir}/toolchain-xtensa@2.40802.200502/xtensa-lx106-elf/include/c++/4.8.2/forward_list

custom_spgm_generator.output_dir = ${platformio.src_dir}/generated
custom_spgm_generator.extra_args =
    --source-dir=${platformio.lib_dir}
    --source-dir=${EXTERNAL_PROJECT_DIR}/lib/*/src/*
    --src-filter-include=${EXTERNAL_PROJECT_DIR}/lib/*
    --src-filter-include=${EXTERNAL_PROJECT_DIR}/lib/*
    --src-filter-include=${EXTERNAL_PROJECT_DIR}/lib/*
    --src-filter-exclude=${EXTERNAL_PROJECT_DIR}/lib/*/tests/*
    --src-filter-exclude=${EXTERNAL_PROJECT_DIR}/lib/*/mock/*
    --src-filter-exclude=${EXTERNAL_PROJECT_DIR}/lib/*/example/*
    --include-file=Arduino_compat.h
    -D__cplusplus=201103L
    -DESP8266=1
```

## Building the example

Building PROGMEM strings for the provided example run

`pio run -t buildspgm -e example`

Forcing a rebuild without any changes detected

`pio run -t rebuildspgm -e example`

After that it can be compiled and uploaded

`pio run -t upload -e example`

To automatically build PROGMEM strings every time a project is compiled, see platformio documentation how to add executing scripts for a target using extra_scripts
