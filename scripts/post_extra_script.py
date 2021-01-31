#
# Author: sascha_lammers@gmx.de
#

try:
    from .spgm_extra_script import SpgmExtraScript
except:
    pass
from SCons.Script.SConscript import SConsEnvironment
from SCons.Script.SConscript import DefaultEnvironmentCall
from generator import SpgmConfig
import generator
import sys

env = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("env")

projenv = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("projenv")

spgm_extra_script = generator.get_spgm_extra_script() # type: SpgmExtraScript

SpgmConfig.verbose('SPGM POSTSCRIPT', True)

spgm_extra_script.add_pre_actions(env)

env.AlwaysBuild(env.Alias("spgm_install_requirements", None, spgm_extra_script.run_install_requirements))
env.AlwaysBuild(env.Alias("spgm_build", None, spgm_extra_script.run_build_spgm))
env.AlwaysBuild(env.Alias("spgm_export_auto", None, spgm_extra_script.run_export_auto))
env.AlwaysBuild(env.Alias("spgm_export_config", None, spgm_extra_script.run_export_config))
env.AlwaysBuild(env.Alias("spgm_export_all", None, spgm_extra_script.run_export_all))

env.AddPreAction("$BUILD_DIR/${PROGNAME}.elf", spgm_extra_script.run_recompile_auto_strings)

# def testx(name, target, soruce, env):
#     print(name, target, source)

# env.AddPreAction("upload", lambda target, source, env: testx('before_upload', target, source, env))
# env.AddPostAction("upload", lambda target, source, env: testx('after_upload', target, source, env))
# env.AddPreAction("buildprog", lambda target, source, env: testx('before_buildprog', target, source, env))
# env.AddPostAction("buildprog", lambda target, source, env: testx('after_buildprog', target, source, env))

# print(projenv.get("PIOBUILDFILES"))
# print(projenv.Dump())

