/**
 * Author: sascha_lammers@gmx.de
 */

#include <Arduino.h>
#include <FlashStringGenerator.h>

FLASH_STRING_GENERATOR_AUTO_INIT(
    AUTO_STRING_DEF(AutoInitExample, "auto test test")
);

PROGMEM_STRING_DEF(Example1, "Example 1");
PROGMEM_STRING_DEF(Example2, "Example 2");
PROGMEM_STRING_DEF(mime_type_text_html, "text/html");
PROGMEM_STRING_DEF(0, "0");
PROGMEM_STRING_DEF(1, "1");
PROGMEM_STRING_DEF(test_str, TEST_STRING);

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
    Serial.print(FSPGM(Example3, "Inline example 3"));
    Serial.print(FSPGM(Example3, "Inline example 3"));
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
    Serial.print(FSPGM(New_string_unused));
    Serial.print(FSPGM(New_string_3);
    char buffer[32];
    snprintf_P(buffer, sizeof(buffer), SPGM(CURRENCY, "%.2f", en-US:"$%.2f", en_CA:"CA$%.2f",en_au:"AU$%.2f",de;es;it;fr;ch:"%.2fEUR"), 0.0);
    delay(1000);
}
