Import("env");
import subprocess
import os
import sys
import inspect
from SCons.Script import ARGUMENTS


def subst_list_non_empty(list):
    return [env.subst(x.strip()) for x in list if x.strip() != '']

def build_spgm(source, target, env):

    python = env.subst("$PYTHONEXE")
    script = os.path.realpath(os.path.dirname((inspect.getfile(inspect.currentframe()))) + os.sep + 'flashstringgen.py')
    output_dir = env.subst(env.GetProjectOption('spgm_generator.output_dir', default='$PROJECT_SRC_DIR/generated'))
    project_src_dir = env.subst("$PROJECT_SRC_DIR")

    args = [
        python,
        script,
        '--output-dir=' + output_dir,
        '--force',
        '-d', project_src_dir
    ]
    verbose = False
    if int(ARGUMENTS.get("PIOVERBOSE", 0)):
        verbose = True

    for define in env['CPPDEFINES']:
        if isinstance(define, str):
            args.append('-D')
            args.append(env.subst(str(define)))
        elif isinstance(define, tuple):
            args.append('-D')
            args.append(define[0] + '=' + env.subst(str(define[1])))

    args.append('-d')
    args.append(project_src_dir)

    src_filter = subst_list_non_empty(' '.join(env.GetProjectOption('src_filter')).split('>'))
    for filter in src_filter:
        if filter[0]=='+':
            args.append('-I')
            args.append(filter[2:])
        elif filter[0]=='-':
            args.append('-E')
            args.append(filter[2:])

    include_paths = env.GetProjectOption('spgm_generator.include_path', default="").split('\n')
    include_paths.extend(env['CPPPATH'])
    include_paths.append(env['PROJECT_INCLUDE_DIR'])
    include_paths = subst_list_non_empty(include_paths)
    for include in include_paths:
        args.append('-i')
        args.append(include)

    extra_args = subst_list_non_empty(env.GetProjectOption('spgm_generator.extra_args', default="").split('\n'))
    args.extend(extra_args)

    if verbose:
        print(' '.join(args))

    popen = subprocess.run(args, shell=True)
    return_code = popen.returncode
    if return_code!=0:
        print('flashstringgen.py failed to run: ' + str(return_code))
        sys.exit(return_code)

env.AlwaysBuild(env.Alias("buildspgm", None, build_spgm))
