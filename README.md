# FlashString Generator for Ardunio

This tool can generate PROGMEM strings from source code. It is based on [pcpp](https://pypi.org/project/pcpp/), a pure python C preprocessor.

Currently "work in progress"

Instead of writing PSTR("This is my text"), SPGM(This_is_my_text) is being used. Running the tool will check all source code and generate 2 files.

Declare a PROGMEM string

PROGMEM_STRING_DECL(This_is_my_text);

define a PROGMEM string

PROGMEM_STRING_DEF(This_is_my_text, "This is my text");

If the definition is not found in the source code, the tool adds it automatically to the auto generated files.

## Using the standalone version

For this example, you can run

python .\scripts\flashstringgen.py -d .\src --force --output-dir=.\src\generated

It will scan all source files in .\src and create the files in .\src\generated.

### FlashStringGeneratorAuto.json

To modify the content of the strings, edit the .json file and run the tool again.

    "Example1": {                   # id of the string
        "auto": "Example1",         # this is the value the tool assigns automatically
        "use_counter": 1,           # shows how often this id is being used
        "default": "Example 1"      # overwrite it with this
    },

### FlashStringGeneratorAuto.h

Include this file when using any PROGMEM strings. You can also see where the strings are being used.

    // src/example.cpp:44
    // src/example.cpp:47
    PROGMEM_STRING_DECL(New_string);
    // src/example.cpp:45
    PROGMEM_STRING_DECL(New_string_2);
    // src/example.cpp:46
    PROGMEM_STRING_DECL(New_string_3);

## Using PlatformIO and extra_scripts

If using PlatformIO, you can use extra_scripts to provide a target that creates the PROGMEM strings.

Simply add

    extra_scripts = scripts/extra_script.py

to your platformio.ini and execute it with

    pio run -t buildspgm

It is using PROJECT_SRC_DIR, CPPPATH, CPPDEFINES and SRC_FILTER for scanning the project.
