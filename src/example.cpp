/**
 * Author: sascha_lammers@gmx.de
 */

#include <Arduino.h>
#include "spgm_string_generator.h"
#include "test_lib.h"

TestClass _test_class;

// fixed definitions
PROGMEM_STRING_DEF(Example1, "Example 1");
PROGMEM_STRING_DEF(Example2, "Example 2");
PROGMEM_STRING_DEF(UnusedStaticExample, "UnusedStaticExample");
PROGMEM_STRING_DEF(mime_type_text_html, "text/html");
PROGMEM_STRING_DEF(0, "0");
PROGMEM_STRING_DEF(1, "1");
PROGMEM_STRING_DEF(test_str, TEST_STRING);

#include "example.h"
#include "example_ignore.h"

// storing strings inside the code
FLASH_STRING_GENERATOR_AUTO_INIT(
    AUTO_STRING_DEF(AutoInitExample, "test default lang", en_EN: "test en_EN", it_IT: "tests it_IT", fr_FR: "fr_FR")
);

#define _STRINGIFY(...)                     ___STRINGIFY(__VA_ARGS__)
#define ___STRINGIFY(...)                   #__VA_ARGS__
#define NEW_STRING_3                        3

void setup() {
    Serial.begin(115200);
}

void loop() {
    auto example1 = SPGM(Example1);
    Serial.print(example1);
    Serial.print(FSPGM(Example2));
    Serial.print(FSPGM(Example3, "Inline Example 3"));
    Serial.print(FSPGM(Example3, "Inline Example 3")); // redefintion requires same value
    Serial.print(FSPGM(mime_type_text_html));
    Serial.print(FSPGM(index_html, "index.html"));
    Serial.print(FSPGM(New_string));
    Serial.print(FSPGM(New_string_2));
    Serial.print(FSPGM(New_string_3));
    Serial.print(FSPGM(New_string));
    Serial.print(FSPGM(new_string, "new string lowercase"));
    Serial.print(FSPGM(0));
    Serial.print(FSPGM(1));
    Serial.print(FSPGM(New_string_3, "My NEW String " _STRINGIFY(NEW_STRING_3) ));
#if 0
    Serial.print(FSPGM(New_string_unused));
#endif
    Serial.print(FSPGM(New_string_3));
    char buffer[32];
    snprintf_P(buffer, sizeof(buffer), SPGM(CURRENCY, "%.2f", en-US:"$%.2f", en_CA:"CA$%.2f",en_au:"AU$%.2f",de;es;it;fr:"%.2fEUR"), 1.5);
    Serial.print(FSPGM(CURRENCY, "%.2f", de;bg: "%.2fEUR")); // redefintion merges translations
    delay(1000);
}
