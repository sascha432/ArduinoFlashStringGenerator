Import("env")
import subprocess
import os
import sys
import inspect

def build_spgm(source, target, env):

    python = env['PYTHONEXE']
    script = os.path.dirname((inspect.getfile(inspect.currentframe()))) + os.sep + 'flashstringgen.py'
    script = os.path.realpath(script)

    args = [
        python,
        script,
        '--output-dir=./src/generated',
        '--force',
        '-d', env['PROJECT_SRC_DIR']
    ]
    verbose = False
    try:
        if '-v' in env['UPLOADERFLAGS']:
            args.append('--verbose')
            verbose = True
    except:
        pass

        if verbose:
            print("Verbose mode on")

    for define in env['CPPDEFINES']:
        if isinstance(define, str):
            args.append('-D')
            args.append(define)
        elif isinstance(define, tuple):
            args.append('-D')
            args.append(define[0] + '=' + str(define[1]))

    args.append('-d')
    dir = env['PROJECT_SRC_DIR']
    args.append(dir)

    for filter in env['SRC_FILTER']:
        filter = filter.split('>')
        for item in filter:
            item = item.strip()
            if len(item):
                if item[0]=='+':
                    item = item[1:].lstrip('<')
                    args.append('-I')
                    args.append(item)
                elif item[0]=='-':
                    item = item[1:].lstrip('<')
                    args.append('-E')
                    args.append(item)

    for include in env['CPPPATH']:
        args.append('-i')
        args.append(include)

    if verbose:
        print(' '.join(args))

    print(' '.join(args))
    subprocess.Popen(args, shell=True)

env.AlwaysBuild(env.Alias("buildspgm", None, build_spgm))
