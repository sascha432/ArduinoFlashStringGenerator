# Changelog

## 0.1.1 (work-in-progress)

- New database format to run multiple processes in parallel (work in progress; since python just uses one core, the preprocessor threads need to be spawned externally)
- PlatformIO 5.0 support
- Cache for configuration
- Fixed exporting static defintion
- Copying locations from build database to database
- Added definition and declaration file to source_excludes/skip_includes

## 0.1.0

- Fully integrated into platformio as middleware
- Standalone version has been removed
- Incremental updates during complication

## 0.0.4

- Incremental updates
- source_dir changed to glob
- Fixed file collector
- Added rebuild option (--force)
- Fixed issues with pcpp 1.22

## 0.0.3

- Reorganized file structure and refactored code
- Added missing include in FlashStringGeneratorAuto.cpp
- Fixed passing CPPDEFINES in extra_script.py
- Adding defines for known BOARD_MCU
- Added extern "C" to include file
- Added FLASH_STRING_GENERATOR_AUTO_INIT (see `include/FlashStringGenerator.h`)

## 0.0.2

- Added `-@/--args-from-file` in case the command line exceeds it length limit
- `extra_scripts.py` adds include and source directories from all libraries (src_filter not supported yet)
- The text default can be defined in C source code
- Support for internationalization and localization
- Ignore #include that are excluded by src_filter

## 0.0.1

- Initial version
