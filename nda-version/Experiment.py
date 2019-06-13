#!/usr/bin/env python3

import os, json, sys
from argparse import ArgumentParser
from pathlib import Path
import subprocess

from inspect import currentframe, getframeinfo
from pprint import pprint
import IPython

import Utils
from Results import *
from SpecBench import *
from CooldownConfig import CooldownConfig

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)

gem5_dir            = Path('..') / 'gem5'
gem5_dir_invisispec = Path('..') / 'invisi_spec' / 'InvisiSpecClone'
# gem5_opt    = gem5_dir / 'build' / 'X86' / 'gem5.opt'
gem5_opt            = gem5_dir / 'build' / 'X86_MESI_Two_Level' / 'gem5.opt'
gem5_opt_invisispec = gem5_dir_invisispec / 'build' / 'X86_MESI_Two_Level' / 'gem5.opt'
gem5_debug          = gem5_dir / 'build' / 'X86' / 'gem5.debug'
gem5_script         = Path('.') / 'se_run_experiment.py' #This script will call RunExperiment below

def PrintFrameInfo( prefix, frameinfo ):
    print( prefix + "%s:%s:%s" % (      os.path.abspath( frameinfo.filename ),
                                        frameinfo.function,
                                        frameinfo.lineno ))

class ExitCause:
    SIMULATION_DONE  = "exiting with last active thread context"
    WORK_BEGIN       = "workbegin"
    SIMULATE_LIMIT   = 'simulate() limit reached'
    VALID_STOP       = [SIMULATION_DONE, SIMULATE_LIMIT]

def ToggleFlags( exit_cause, flags ):
    import m5
    if exit_cause == ExitCause.WORK_BEGIN:
        for flagName in flags:
            # print( "Enabling flag %s" % flagName )
            m5.debug.flags[ flagName ].enable()
    else:
        for flagName in flags:
            m5.debug.flags[ flagName ].disable()


def RunExperiment( options, root, system, FutureClass ):
    # The following are imported here, since they will be available when RunExperiment
    # will be called from within gem5:
    from common import Simulation
    import m5
    import m5.core

    PrintFrameInfo( "Launching ", getframeinfo(currentframe()) )
    # IPython.embed()
    # This flag must be set to True to enable exits on "m5_work*"
    # system.exit_on_work_items = True

    #Just initialize, don't run simulation

    exit_cause = None
    system.exit_on_work_items = True

    before_init_config, after_warmup_config = CooldownConfig.get_config(
        options.cooldown_config)

    checkpoint_in = Path('.')
    if options.checkpoint is not None:
        checkpoint_in = Path(options.checkpoint)

    num_warmup_insts = int(options.warmup_insts)
    real = int(options.reportable_insts)

    outdir = Path('gem5') / checkpoint_in.name
    if options.outdir is not None:
        print('OUTDIR = {}'.format(options.outdir))
        outdir = Path(options.outdir)

    if not outdir.exists():
        outdir.mkdir(parents=True)

    print(outdir)
    m5.core.setOutputDir(str(outdir))

    stats_file = Utils.StatsFile(outdir / 'stats.txt')
    res_file = outdir / 'res.json'

    runType = RunType.OUT_OF_ORDER
    if options.cpu_type == 'TimingSimpleCPU':
        runType = RunType.IN_ORDER
    elif options.invisispec:
        runType = RunType.INVISISPEC
    elif options.cooldown_config != 'empty':
        runType = RunType.COOLDOWN

    resobj = Results(runType, Path(options.cmd).name, stats_file,
                     options.cooldown_config)

    before_init_config(system)

    if options.checkpoint is not None:
        assert checkpoint_in.exists()
        m5.instantiate(str(checkpoint_in))
    else:
        m5.instantiate()

    #m5.debug.flags[ 'Fetch' ].enable()

    try:
        limit = max(int(num_warmup_insts * 0.05 * 500), 1000 * 500)
        warmup_insts_done = 0
        print('**** WARMUP SIMULATION ({} instructions, {} cycle granularity) ****'.format(
          num_warmup_insts, limit))

        
        # m5.debug.flags[ "CacheAccess" ].enable() 
        # m5.debug.flags[ "RubyGenerated" ].enable() 
        while warmup_insts_done < num_warmup_insts:
            exit_event = m5.simulate(limit)
            exit_cause = exit_event.getCause()
            if exit_cause != ExitCause.SIMULATE_LIMIT:
                print( '='*10 + ' Exiting @ tick %i because %s' % ( m5.curTick(), exit_cause ) )
                print(exit_cause)
                return

            stats             = stats_file.get_current_stats()
            warmup_insts_done = int(stats['sim_insts'])
            percentCompleted  = ( float(warmup_insts_done) / num_warmup_insts ) * 100
            print('{:5.2f}% inst: {}/{}'.format(
              percentCompleted, warmup_insts_done, num_warmup_insts))

        resobj.get_warmup_stats()
        after_warmup_config()

        realInstructionsDone = 0
        limit = max(int(real * 0.05 * 500), 1000 * 500)
        print('**** REAL SIMULATION ({} instructions, {} cycle granularity) ****'.format(
          'unlimited' if real < 0 else real, limit))
        while realInstructionsDone < real or real < 0:
            exit_event = m5.simulate(limit)
            exit_cause = exit_event.getCause()

            stats                 = stats_file.get_current_stats()
            realInstructionsDone  = int(stats['sim_insts']) - warmup_insts_done
            percentCompleted      = float(realInstructionsDone) / real * 100
            print('{:5.2f}% Completed instructions: {}/{} '.format(
              percentCompleted, realInstructionsDone, real))
            if exit_cause != ExitCause.SIMULATE_LIMIT:
                break

        print( '='*10 + ' Exiting @ tick %i because %s' % ( m5.curTick(), exit_cause ) )

        resobj.get_final_stats()

        resobj.dump_stats_to_file(res_file)

        print('Results:')
        df = resobj.human_stats()
        pprint(df)


    except Exception as e:
        if isinstance(e, AssertionError) or isinstance(e, KeyError):
            import IPython
            IPython.embed()
            raise
        print('{} raised: {}'.format(type(e), e))
        import IPython
        IPython.embed()

def create_gem5_command(bin_path, bin_args, cpu_type='DerivO3CPU', extra_se_args=[],
    gem5_debug_args=[], debug_mode=False, runInvisiSpec = False, invisiSpecScheme = None):
    if not bin_path.exists():
        print('Error: {} does not exist.'.format(str(bin_path)))
        return -1

    se_py_args = [#'--help',
                  # '--mem-type', 'DDR3_1600_8x8',
                  '--mem-type', 'SimpleMemory',
                  #'--mem-size', '512MB',
                  # '--list-mem-types',
                  '--cmd', str(bin_path),
                  #'--list-cpu-types',
                  '--cpu-type', str(cpu_type),
                  '--cpu-clock', '2GHz',
                  '--sys-clock', '2GHz',
                  '--l1d_size', '32kB',
                  '--l1d_assoc', '8',
                  '--l1i_size', '32kB',
                  '--l1d_assoc', '8',
                  '--l2_size',  '2MB',
                  '--l2_assoc',  '16',
                  '--l2cache',
                  '--ruby',
                  '--network=simple', '--topology=Mesh_XY', '--mesh-rows=1',
                  # L3 caches don't work by default.
                  # '--l3_size',  '8MB',
                  '--caches',
                  ] + extra_se_args + gem5_debug_args

    if (len(bin_args) > 0):
        se_py_args += ['--options', '{}'.format(' '.join(bin_args))]

    if debug_mode:
        gem5_opt_args = ['gdb', '--args', str(gem5_debug) ]

    if runInvisiSpec:
        gem5_opt_args = [ str(gem5_opt_invisispec) ]
        gem5_args = gem5_opt_args        +\
                    [str(gem5_script) ]  +\
                    se_py_args           +\
                    ['--invisispec',
                     '--scheme=%s' % invisiSpecScheme,
                     '--needsTSO=1', ]
    else:
        gem5_opt_args = [ str(gem5_opt) ]
        gem5_args = gem5_opt_args + [str(gem5_script) ] + se_py_args

    return gem5_args


def run_binary_on_gem5(bin_path, bin_args, parsed_args):
    extra_args = [# '--help',
        '--warmup-insts', str(parsed_args.warmup_insts),
        '--reportable-insts', str(parsed_args.reportable_insts),
    ]
    debug_args = []
    if parsed_args.start_checkpoint is not None:
        extra_args += [ '--start-checkpoint', str(parsed_args.start_checkpoint) ]
        mappings_file = Path(parsed_args.start_checkpoint) / 'mappings.json'
        if not mappings_file.exists():
            raise Exception('{} does not exist!'.format(str(mappings_file)))
        mem_size = Utils.get_mem_size_from_mappings_file(mappings_file)
        extra_args += [ '--mem-size', str(mem_size) ]
    else:
        extra_args += [ '--mem-size', str(parsed_args.mem_size) ]

    if parsed_args.cooldown_config:
        debug_args += [ '--cooldown-config', parsed_args.cooldown_config ]
    if parsed_args.output_dir is not None:
        extra_args += [ '--outdir', str(parsed_args.output_dir) ]

    gem5_args = []
    if parsed_args.in_order:
        gem5_args = create_gem5_command(bin_path, bin_args,
            cpu_type='TimingSimpleCPU', extra_se_args=extra_args,
            gem5_debug_args=debug_args, debug_mode=parsed_args.debug_mode)
    else:
        gem5_args = create_gem5_command( bin_path,
                                         bin_args,
                                         extra_se_args    = extra_args,
                                         gem5_debug_args  = debug_args,
                                         debug_mode       = parsed_args.debug_mode,
                                         runInvisiSpec    = parsed_args.invisispec,
                                         invisiSpecScheme = parsed_args.scheme)

    # GLIBC_VERSION = '2.27'
    # GLIBC_DIR = Path('..') / 'glibc-{}'.format(GLIBC_VERSION) / 'install' / 'lib'

    # assert GLIBC_DIR.exists()

    # # TODO: do this per benchmark
    # GLIBC_SHARED_OBJECTS = [ str(f) for f in GLIBC_DIR.iterdir()
    #     if f.is_file() and GLIBC_VERSION in f.name and 'so' in f.name and 'ld' not in f.name]
    # LD_PRELOAD_STR = ' '.join(GLIBC_SHARED_OBJECTS)
    # os.environ['LD_PRELOAD'] = LD_PRELOAD_STR
    return subprocess.call(gem5_args, env=os.environ)

def do_make(target=''):
    ret = os.system('make {}'.format(target))
    if ret != 0:
        raise Exception('make FAILED with code {}'.format(ret))

def add_experiment_args(parser):
    parser.add_argument('--warmup-insts', type=int,
                        help='Number of instructions to run before reporting stats',
                        default=5000000)
    parser.add_argument('--reportable-insts', type=int,
                        help=('Arguments to supply to simulated executable. If '
                        '-1, run until end of program.'), default=100000)
    parser.add_argument('--output-dir', default=None,
                        help=('Directory for gem5 stats and experiment results. '
                        'Default is gem5/[CHECKPOINT NAME]/{res.json,stats.txt}'))
    parser.add_argument('--in-order', action='store_true',
                        default=False, help='Use timing CPU instead of O3CPU')
    parser.add_argument('--mem-size', '-m', default='1GB',
    help='Size of memory to use. If checkpoint exists, reads from mappings.json')
    parser.add_argument('--debug-mode', default=False, action='store_true',
        help='Run gem5.debug in gdb instead of gem5.opt.')

    # [InvisiSpec] add options to configure needsTSO and scheme
    parser.add_argument("--scheme", default="UnsafeBaseline",
            choices=["UnsafeBaseline", "FuturisticSafeFence",
            "SpectreSafeFence", "FuturisticSafeInvisibleSpec",
            "SpectreSafeInvisibleSpec"],
            help="Used together with --invisispec. Choose baseline or defense designs to evaluate")

    parser.add_argument('--invisispec', default=False, action='store_true',
        help='Run InvisiSpec Gem5')

def main():
    parser = ArgumentParser(description=
      'Run a standard gem5 configuration with a custom binary.')

    SpecBench.add_parser_args(parser)
    add_experiment_args(parser)
    CooldownConfig.add_parser_args(parser)

    parser.add_argument('--start-checkpoint',
                        default=None, help=('Checkpoint to start simulating from.'
                        'If not given, starts from program beginning'))

    parser.add_argument('--binary', help='compiled binary file path')
    parser.add_argument('--args',
                        help='Arguments to supply to simulated executable',
                        default='', nargs='+')

    args = parser.parse_args()

    if args.bench is not None and args.binary is not None:
        raise Exception('Can only pick one!')

    SpecBench.maybe_display_spec_info(args)
    CooldownConfig.maybe_show_configs(args)

    exp_bin = args.binary
    exp_args = args.args
    if args.bench:
        benchmarks = SpecBench.get_benchmarks(args)
        if len(benchmarks) != 1:
            raise Exception('Experiment.py only supports a single task!')
        benchmark = benchmarks[0]

        bench = SpecBench().create(args.suite, benchmark, args.input_type)
        exp_bin = bench.binary
        exp_args = bench.args

    return run_binary_on_gem5(Path(exp_bin), exp_args, args)


if __name__ == '__main__':
    exit(main())
