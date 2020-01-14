import os, json, sys, copy
from argparse import ArgumentParser
from pathlib import Path
import subprocess

from inspect import currentframe, getframeinfo
from pprint import pprint
import IPython

try:
    from lapidary.utils import *
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from lapidary.utils import *

from lapidary.config import LapidaryConfig, Gem5FlagConfig
from lapidary.config.specbench.SpecBench import *
from lapidary.report.Results import *

WORK_DIR = os.path.dirname(__file__)
if len( WORK_DIR ) == 0:
    WORK_DIR = "."

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)

gem5_dir    = Path('..') / 'gem5'
sys.path.append(str(gem5_dir / '/configs/'))
gem5_opt    = gem5_dir / 'build' / 'X86' / 'gem5.opt'
gem5_debug  = gem5_dir / 'build' / 'X86' / 'gem5.debug'
gem5_script = Path(__file__).parent / 'se_run_experiment.py' #This script will call RunExperiment below
pythonpath = ''

def PrintFrameInfo(prefix, frameinfo):
    print("%s%s:%s:%s" % (  prefix, 
                            os.path.abspath( frameinfo.filename ),
                            frameinfo.function,
                            frameinfo.lineno ))

class ExitCause:
    SIMULATION_DONE  = "exiting with last active thread context"
    WORK_BEGIN       = "workbegin"
    SIMULATE_LIMIT   = 'simulate() limit reached'
    VALID_STOP       = [SIMULATION_DONE, SIMULATE_LIMIT]

def ToggleFlags(exit_cause, flags):
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

    config = LapidaryConfig(options.config_file)
    Gem5FlagConfig.parse_plugins(config)

    before_init_config, after_warmup_config = Gem5FlagConfig.get_config(
        options.flag_config)

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

    stats_file = StatsFile(outdir / 'stats.txt')
    res_file = outdir / 'res.json'

    runType = RunType.OUT_OF_ORDER
    if options.cpu_type == 'TimingSimpleCPU':
        runType = RunType.IN_ORDER
    if options.flag_config != 'empty':
        runType = RunType.COOLDOWN

    resobj = Results(runType, Path(options.cmd).name, stats_file,
        options.flag_config)

    before_init_config(system)

    cpu = system.cpu[0]

    if options.checkpoint is not None:
        assert checkpoint_in.exists()
        m5.instantiate(str(checkpoint_in))
    else:
        m5.instantiate()

    try:
        limit = max(int(num_warmup_insts * 0.01 * 500), 1000 * 500)
        warmup_insts_done = 0
        print('**** WARMUP SIMULATION ({} instructions, {} cycle granularity) ****'.format(
          num_warmup_insts, limit))

        quit = False
        while warmup_insts_done < num_warmup_insts:
            exit_event = m5.simulate(limit)
            exit_cause = exit_event.getCause()
            if exit_cause != ExitCause.SIMULATE_LIMIT:
                print( '='*10 + ' Exiting @ tick %i because %s' % ( m5.curTick(), exit_cause ) )
                quit = True

            stats             = stats_file.get_current_stats()
            warmup_insts_done = int(stats['sim_insts'])
            percentCompleted  = ( float(warmup_insts_done) / num_warmup_insts ) * 100
            print('{:5.2f}% inst: {}/{}'.format(
              percentCompleted, warmup_insts_done, num_warmup_insts))

            if quit:
                return

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
    gem5_debug_args=[], debug_mode=False):
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
                  # L3 caches don't work by default.
                  # '--l3_size',  '8MB',
                  '--caches',
                  ] + extra_se_args + gem5_debug_args

    if (len(bin_args) > 0):
        se_py_args += ['--options', '{}'.format(' '.join(bin_args))]

    gem5_opt_args = [ str(gem5_opt) ]
    if debug_mode:
        gem5_opt_args = ['gdb', '--args', str(gem5_debug) ]

    gem5_args = gem5_opt_args + [str(gem5_script) ] + se_py_args

    return gem5_args


def run_binary_on_gem5(bin_path, bin_args, parsed_args):
    extra_args = [# '--help',
        '--warmup-insts', str(parsed_args.warmup_insts),
        '--reportable-insts', str(parsed_args.reportable_insts),
        '--config', str(parsed_args.config.filename)
    ]

    if parsed_args.syscalls_hook:
        extra_args += ['--syscalls-hook' ]

    debug_args = []
    if parsed_args.start_checkpoint is not None:
        extra_args += [ '--start-checkpoint', str(parsed_args.start_checkpoint) ]
        mappings_file = Path(parsed_args.start_checkpoint) / 'mappings.json'
        if not mappings_file.exists():
            raise Exception('{} does not exist!'.format(str(mappings_file)))
        mem_size = get_mem_size_from_mappings_file(mappings_file)
        extra_args += [ '--mem-size', str(mem_size) ]
    else:
        extra_args += [ '--mem-size', str(parsed_args.mem_size) ]

    if hasattr(parsed_args, 'flag_config') and parsed_args.flag_config:
        debug_args += [ '--flag-config', parsed_args.flag_config ]
    if parsed_args.output_dir is not None:
        extra_args += [ '--outdir', str(parsed_args.output_dir) ]

    gem5_args = []
    if parsed_args.in_order:
        gem5_args = create_gem5_command(bin_path, bin_args,
            cpu_type='TimingSimpleCPU', extra_se_args=extra_args,
            gem5_debug_args=debug_args, debug_mode=parsed_args.debug_mode)
    else:
        gem5_args = create_gem5_command(bin_path, bin_args, extra_se_args=extra_args,
            gem5_debug_args=debug_args, debug_mode=parsed_args.debug_mode)

    # GLIBC_VERSION = '2.27'
    # GLIBC_DIR = Path('..') / 'glibc-{}'.format(GLIBC_VERSION) / 'install' / 'lib'

    # assert GLIBC_DIR.exists()

    # # TODO: do this per benchmark
    # GLIBC_SHARED_OBJECTS = [ str(f) for f in GLIBC_DIR.iterdir()
    #     if f.is_file() and GLIBC_VERSION in f.name and 'so' in f.name and 'ld' not in f.name]
    # LD_PRELOAD_STR = ' '.join(GLIBC_SHARED_OBJECTS)
    # os.environ['LD_PRELOAD'] = LD_PRELOAD_STR
    env = copy.deepcopy(os.environ)
    env['PYTHONPATH'] = str(pythonpath)
    # iangneal: we are explicit with the stdout/stderr so that we preserve any
    # prior redirection.
    return subprocess.call(gem5_args, 
                           env=env, stdout=sys.stdout, stderr=sys.stderr)


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

    parser.add_argument('--start-checkpoint',
                        default=None, help=('Checkpoint to start simulating from.'
                        'If not given, starts from program beginning'))

    parser.add_argument('--binary', help='compiled binary file path')
    parser.add_argument('--args',
                        help='Arguments to supply to simulated executable',
                        default='', nargs='+')
    parser.add_argument('--syscalls-hook', action='store_true',
                        default=False, help='Use strace log to replace syscalls')

    Gem5FlagConfig.add_parser_args(parser)
    SpecBench.add_parser_args(parser)

def do_experiment(args, config=None):
    
    global gem5_dir
    global gem5_opt
    global gem5_debug
    global pythonpath

    if config is not None:
        args.config = config

    gem5_dir    = args.config['gem5_path']
    gem5_opt    = gem5_dir / 'build' / 'X86' / 'gem5.opt'
    gem5_debug  = gem5_dir / 'build' / 'X86' / 'gem5.debug'
    pythonpath  = gem5_dir / 'configs'

    if args.bench is not None and args.binary is not None:
        raise Exception('Can only pick one!')

    exp_bin = args.binary
    exp_args = args.args
    if args.bench:
        benchmarks = SpecBench.get_benchmarks(args)
        if len(benchmarks) != 1:
            raise Exception('Experiment.py only supports a single task!')
        benchmark = benchmarks[0]

        bench = SpecBench(args.config).create(args.suite, benchmark, args.input_type)
        exp_bin = bench.binary
        exp_args = bench.args

    return run_binary_on_gem5(Path(exp_bin), exp_args, args)
