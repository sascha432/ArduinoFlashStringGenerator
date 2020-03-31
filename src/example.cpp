/**
 * Author: sascha_lammers@gmx.de
 */

// python .\scripts\flashstringgen.py -d .\src  --output-dir=.\src\generated  -v
// python .\scripts\flashstringgen.py -v -d ..\kfc_fw\src -d ..\kfc_fw\include --output-dir tmp/ --database tmp/.flashstringgen -D ESP8266

#include <Arduino.h>
#include <FlashStringGenerator.h>

PROGMEM_STRING_DEF(Example1, "Example 1");
PROGMEM_STRING_DEF(Example2, "Example 2");
PROGMEM_STRING_DEF(text_html, "text/html");
PROGMEM_STRING_DEF(0, "0");
PROGMEM_STRING_DEF(1, "1");
PROGMEM_STRING_DEF(test_str, TEST_STRING);

void setup() {
    Serial.begin(115200);

}

void loop() {
    Serial.print(SPGM(Example1));
    Serial.print(SPGM(Example2));
    Serial.print(FSPGM(text_html));
    Serial.print(SPGM(New_string));
    Serial.print(SPGM(New_string_2));
    Serial.print(SPGM(New_string_3));
    Serial.print(SPGM(New_string));
    Serial.print(SPGM(0));
    Serial.print(SPGM(1));
    Serial.print(SPGM(MACRO_AS_ID));
    Serial.print(TEST_DEF);
    delay(1000);
}
