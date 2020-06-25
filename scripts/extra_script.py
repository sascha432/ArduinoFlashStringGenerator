Import("env");
import subprocess
import os
from os import path
import sys
import inspect
import shlex
from SCons.Script import ARGUMENTS
import tempfile


def subst_list_non_empty(list):
    return [env.subst(x.strip()) for x in list if x.strip() != '']

def build_spgm(source, target, env):

    # use flash generatored from .. where extra_scripts.py is locatated
    script = path.realpath(path.join(path.dirname((inspect.getfile(inspect.currentframe()))), 'flashstringgen.py'))

    args_file = tempfile.NamedTemporaryFile('w+t', delete=False)

    args = [
        env.subst("$PYTHONEXE"),
        script,
        '-p', env.subst("$PROJECT_DIR"),
        '--output-dir=' + env.subst(env.GetProjectOption('custom_spgm_generator.output_dir', default='$PROJECT_SRC_DIR/generated')),
        '-d', env.subst("$PROJECT_SRC_DIR"),
        '-@', args_file.name
    ]

    verbose = False
    if int(ARGUMENTS.get("PIOVERBOSE", 0)):
        verbose = True
        args.append('--verbose')

    for define in env['CPPDEFINES']:
        if isinstance(define, str):
            args_file.write('-D' + env.subst(str(define)) + '\n');
        elif isinstance(define, tuple):
            args_file.write('-D' + define[0] + '=' + env.subst(str(define[1])) + '\n');

    args_file.write('-D__cplusplus=201103L\n');

    mmcu = env.subst("$BOARD_MCU").lower()
    if mmcu=="esp8266":
        args_file.write('-DESP8266=1\n');
    elif mmcu=="esp32":
        args_file.write('-DESP32=1\n');
    elif mmcu=="atmega328p":
        args_file.write('-D__AVR__=1\n');
        args_file.write('-D__AVR_ATmega328P=1\n');
    elif mmcu=="atmega328pb":
        args_file.write('-D__AVR__=1\n');
        args_file.write('-D__AVR_ATmega328PB=1\n');
    elif mmcu=="atmega48p":
        args_file.write('-D__AVR__=1\n');
        args_file.write('-D__AVR_ATmega48P=1\n');
    elif mmcu=="atmega88p":
        args_file.write('-D__AVR__=1\n');
        args_file.write('-D__AVR_ATmega88P=1\n');
    elif mmcu=="atmega168p":
        args_file.write('-D__AVR__=1\n');
        args_file.write('-D__AVR_ATmega168P=1\n');
    else:
        print("WARNING: -mmcu=%s not supported. Some defines might be missing. Check https://gcc.gnu.org/onlinedocs/gcc/AVR-Options.html for a full list" % mmcu);

    src_filter = subst_list_non_empty(' '.join(env.GetProjectOption('src_filter')).split('>'))
    for filter in src_filter:
        if filter[0]=='+':
            args_file.write('-I\n')
            args_file.write(filter[2:] + '\n')
        elif filter[0]=='-':
            args_file.write('-E\n')
            args_file.write(filter[2:] + '\n')

    include_paths = env.GetProjectOption('custom_spgm_generator.include_path', default="").split('\n')
    include_paths.extend(env['CPPPATH'])
    include_paths.append(env['PROJECT_INCLUDE_DIR'])
    include_paths = subst_list_non_empty(include_paths)
    for include in include_paths:
        args_file.write('-i\n')
        args_file.write(include + '\n')

    for libs in env['__PIO_LIB_BUILDERS']:
        if libs.include_dir:
            args_file.write('-i\n')
            args_file.write(libs.include_dir + '\n')
        if libs.src_dir:
            args_file.write('-i\n')
            args_file.write(libs.src_dir + '\n')
        # TODO
        # if libs.src_filter:
        #     print(libs.src_filter)


    extra_args = subst_list_non_empty(env.GetProjectOption('custom_spgm_generator.extra_args', default="").split('\n'))
    for arg in extra_args:
        args_file.write(arg + '\n');

    args.append('2>&1')

    if verbose:
        parts = []
        for arg in args:
            parts.append(shlex.quote(arg))
        parts[0] = args[0]
        print(' '.join(parts))

    args_file.close();
    try:
        popen = subprocess.run(args, shell=True)
    except Exception as e:
        raise e
    finally:
        os.unlink(args_file.name);

    return_code = popen.returncode
    if return_code!=0:
        print('flashstringgen.py failed to run: ' + str(return_code))
        sys.exit(return_code)

env.AlwaysBuild(env.Alias("buildspgm", None, build_spgm))
