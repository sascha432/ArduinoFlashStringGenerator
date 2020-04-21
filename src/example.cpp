/**
 * Author: sascha_lammers@gmx.de
 */

#include <Arduino.h>
#include "FlashStringGenerator.h"

PROGMEM_STRING_DEF(Example1, "Example 1");
PROGMEM_STRING_DEF(Example2, "Example 2");
PROGMEM_STRING_DEF(mime_type_text_html, "text/html");
PROGMEM_STRING_DEF(0, "0");
PROGMEM_STRING_DEF(1, "1");
PROGMEM_STRING_DEF(test_str, TEST_STRING);

void setup() {
    Serial.begin(115200);
}

void loop() {
    Serial.print(FSPGM(Example1));
    Serial.print(FSPGM(Example2));
    Serial.print(FSPGM(mime_type_text_html));

    // will become "Auto Test". The values can be edited in FlashStringGeneratorAuto.json
    Serial.print(FSPGM(Auto_Test));

    // Define this string for all languages, shortcut for "{'*': 'New String translation'}"
    Serial.print(FSPGM(New_string, "New String translation"));
    Serial.print(FSPGM(New_string));
    Serial.print(FSPGM(New_string));

    Serial.print(FSPGM(New_string_2, "{'*':'New String 2','de':'Neue Zeichenkette 2','fr':'nouvelle chaîne 2'}"));  // Define de and fr, * is the fallback if no translation exists
    Serial.print(FSPGM(New_string_3, "New String 3"));
    Serial.print(FSPGM(New_string_3, "New String 3")); // redefinition is ok as long as it is the same
    // Serial.print(FSPGM(New_string_3, "New String 3 - Different annotation will cause an error"));
    Serial.print(FSPGM(0));
    Serial.print(FSPGM(1));
    Serial.print(FSPGM(test_str));
    delay(1000);
}
