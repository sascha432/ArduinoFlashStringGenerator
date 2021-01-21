# FlashString Generator for Ardunio with internationalization and localization

This tool can generate PROGMEM strings from source code. It is based on [pcpp](https://pypi.org/project/pcpp/), a pure python C preprocessor.

Instead of writing `PSTR("This is my text!")`, `SPGM(This_is_my_text_)` or `SPGM(This_is_my_text_, "This is my text!"))` is being used. Running the tool will check all source code and generate the defined flash strings.

## Change Log

[Change Log v0.0.3](CHANGELOG.md)

## Requirements

- pcpp

Install pcpp in a directory that is in the PIO path, for example

```
pip install pcpp --prefix $HOME\.platformio\penv

or

pip install pcpp --prefix ~/.platformio/penv
```

## Basic usage

### Declaring a PROGMEM string (in header files)

`PROGMEM_STRING_DECL(id)`

`PROGMEM_STRING_DECL(This_is_my_text);`

### Defining a PROGMEM string statically (in source files)

`PROGMEM_STRING_DECL(id, "Default text")`

`PROGMEM_STRING_DEF(This_is_my_text, "This is my text");`

### Using a PROGMEM string

The tool will create the PROGMEM string automatically if it is not statically.

`SPGM(id)` (const char \*) or `FSPGM(id)` (const __FlashStringHelper \*)

### Modifying the text

The tool will try to create a beautified version of the name.

For example: This_is_my_text = "This is my text"

To avoid this, the default can be added to the macro. This needs to be done once and in case the default is redefined differently, it will cause an error.

`SPGM(_pictures_index_html, "/pictures/index.html")`

Strings that are not being used anymore are removed from the C source, but kept in `FlashStringGeneratorAuto.json`

### Internationalization and localization

Besides the "default" translation, it is possible to define different language.

`SPGM(CURRENCY, "%.2f", en-US:"$%.2f", en_CA:"CA$%.2f",en_au:"AU$%.2f",de;es;it;fr;ch:"%.2fEUR")`

#### Using a different language

To create flashs strings for a different language, use the argument `--i18n`

`--i18n=en-US`
`--i18n=en-CA`
`--i18n=en-GB`
`--i18n=fr-CH`
`--i18n=de-CH`
`--i18n=it`

If the translation `en-CA` is missing, the first fallback is `en`, the second `en-*` and then `default` (non-case sensitive, - and _ are treated equally). To change this behavior, the order can be specified.

`--i18n=en-US,en,en-CA,en-GB,en-*,default`

### More examples

```
#define TEXT_MACRO "macro"
auto str = SPGM(macro_test, "This is using a " TEXT_MACRO);
```

```
#define MACRO_AS_ID "test_str"
auto str = SPGM(MACRO_AS_ID, "Test String");
```

```
auto str = SPGM(CURRENCY, "%.2f");
```

... [example.cpp](src/example.cpp)

## Using the standalone version

For this example, you can run

python .\scripts\flashstringgen.py -d .\src -S '+<*> -<ignore_me.cpp>' --output-dir=.\src\generated

It will scan all source files in .\src, except ignore_me.cpp and create the files in .\src\generated.

### FlashStringGeneratorAuto.json

To modify the content of the strings, edit the .json file and run the tool again. If the default is defined in the source code, it cannot be changed in this file.

```
    "Example1": {                   # id of the string
        "auto": "Example1",         # this is the value the tool assigns automatically
                                    # once "default" is set, this value will be removed
        "use_counter": 2,           # shows how often this id is being used
        "default": "Example #1"     # overwrite it with this
        "i18n": {
            "en-US": "Example #1 US version",
            "en-CA": "Example #1 CA version",
            "en-GB": "Example #1 GB version",
            "de-CH": "Beispiel #1",
            "fr-CH": "Exemple #1"
        }
    },
    "CURRENCY": {
        "default": "%.2f",
        "i18n": {
            "en-US": "$%.2f",
            "en-CA": "CA$%.2f",
            "de": "%.2f€",
        }
    }
```

### FlashStringGeneratorAuto.h

Include this file when using any PROGMEM strings. You can also see where the strings are being used.

```
// src/example.cpp:44
// src/example.cpp:47
PROGMEM_STRING_DECL(New_string);
// src/example.cpp:45
PROGMEM_STRING_DECL(New_string_2);
// src/example.cpp:46
PROGMEM_STRING_DECL(New_string_3);
```

## Using PlatformIO and extra_scripts

If using PlatformIO, you can use extra_scripts to provide a target that creates the PROGMEM strings.

Simply add `extra_scripts = scripts/extra_script.py` to your platformio.ini and execute it with `pio run -t buildspgm`

If external libraries are used, src_filter for those is not supported.

## Building the example

Building flash strings for the provided example:

`pio run -t buildspgm -e example`

After that it can be compiled and uploaded:

`pio run -t upload -e example`
