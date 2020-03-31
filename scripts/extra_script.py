Import("env")
import subprocess

def build_spgm(source, target, env):
    args = [
        'python',
        './scripts/flashstringgen.py',
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
        args.append('-S')
        args.append(filter)

    for include in env['CPPPATH']:
        args.append('-i')
        args.append(include)

    if verbose:
        print(' '.join(args))

    subprocess.Popen(args, shell=True)

env.AlwaysBuild(env.Alias("buildspgm", None, build_spgm))
