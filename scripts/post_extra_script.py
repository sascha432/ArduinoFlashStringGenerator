#
# Author: sascha_lammers@gmx.de
#

try:
    from .spgm_extra_script import SpgmExtraScript
except:
    pass
from SCons.Script.SConscript import SConsEnvironment
from SCons.Script.SConscript import DefaultEnvironmentCall
from SCons.Script import COMMAND_LINE_TARGETS
from generator import SpgmConfig
import generator
import sys
import click

env = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("env")

projenv = None # type: SConsEnvironment
DefaultEnvironmentCall('Import')("projenv")

spgm_extra_script = generator.get_spgm_extra_script() # type: SpgmExtraScript

SpgmConfig.verbose('SPGM POSTSCRIPT', True)

spgm_extra_script.init_spgm_build(projenv)

if not 'spgm_build' in COMMAND_LINE_TARGETS:
    config = SpgmConfig(env)
    auto_run = config.auto_run
    if auto_run=='always':
        SpgmConfig.verbose('SPGM generator auto run: always')
        spgm_extra_script.add_pre_actions(env)
    elif auto_run=='rebuild':
        SpgmConfig.verbose('SPGM generator auto run: rebuild')
        if config.is_clean or config.is_first_run:
            spgm_extra_script.add_pre_actions(env)
    else:
        SpgmConfig.verbose('SPGM generator auto run: never')

env.AlwaysBuild(env.Alias("spgm_install_requirements", None, spgm_extra_script.run_install_requirements))
env.AlwaysBuild(env.Alias("spgm_build", None, spgm_extra_script.run_spgm_build))
