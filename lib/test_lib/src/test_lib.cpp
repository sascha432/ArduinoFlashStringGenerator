
#include "test_lib.h"
#include <spgm_string_generator.h>

TestClass::TestClass() : _test(12345)
{
    Serial.print(FSPGM(test_class_output, "test class output"));
}
