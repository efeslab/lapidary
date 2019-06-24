import gzip, json, os, re, resource, signal, shutil, subprocess, sys, copy

import glob, shlex

from argparse import ArgumentParser
from elftools.elf.elffile import ELFFile
from multiprocessing import Process
from pathlib import Path
from pprint import pprint
from subprocess import Popen, TimeoutExpired

def join(self, timeout):
    try:
        self.wait(timeout)
    except TimeoutExpired:
        pass

def is_alive(self):
    return self.returncode is None

Popen.join     = join
Popen.is_alive = is_alive

from tempfile import NamedTemporaryFile
from time import sleep

WORK_DIR = os.path.dirname(__file__)
if len( WORK_DIR ) == 0:
    WORK_DIR = "."
sys.path.append( WORK_DIR )

try:
    from lapidary.config.specbench.SpecBench import *
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from lapidary.config.specbench.SpecBench import *

from lapidary.checkpoint.Checkpoints import GDBCheckpoint
from lapidary.checkpoint.CheckpointTemplate import *
import lapidary.checkpoint.CheckpointConvert
from lapidary.config import LapidaryConfig
from lapidary.checkpoint.GDBEngine import GDBEngine

GLIBC_PATH = Path('../libc/glibc/build/install/lib').resolve()
LD_LIBRARY_PATH_STR = '{}:/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu'.format(GLIBC_PATH)

class GDBProcess:
    ''' This is to set up a subprocess that runs gdb for us. '''
    def __init__(self, arg_list,
                       checkpoint_interval=None,
                       checkpoint_instructions=None,
                       checkpoint_locations=None,
                       max_checkpoints=-1,
                       root_dir='.',
                       compress=False,
                       convert=True,
                       debug_mode=False,
                       ld_path=None):

        set_arg_string = 'set $args = "{}"'.format(' '.join(arg_list))
        print(set_arg_string)
        self.args = ['gdb', '--batch', '-ex', set_arg_string, '-x', __file__]

        env = copy.deepcopy(os.environ)

        if checkpoint_instructions is not None:
            env['CHECKPOINT_INSTS']    = str(checkpoint_instructions)
        elif checkpoint_locations is not None:
            env['CHECKPOINT_LOCS']     = ' '.join(checkpoint_locations)
        elif checkpoint_interval is not None:
            env['CHECKPOINT_INTERVAL'] = str(checkpoint_interval)

        env['CHECKPOINT_MAXIMUM']    = str(max_checkpoints)
        env['CHECKPOINT_DEBUG']      = str(debug_mode)
        env['CHECKPOINT_ROOT_DIR']   = str(root_dir)
        env['CHECKPOINT_COMPRESS']   = str(compress)
        env['CHECKPOINT_CONVERT']    = str(convert)

        if ld_path is not None:
            assert ld_path.exists()
            env['CUSTOM_LD'] = str(ld_path)

        self.env = env

    def run(self):
        subprocess.run(self.args)


def add_arguments(parser):
    parser.add_argument('--cmd',
        help='Run a custom command instead of a SPEC benchmark', nargs='*')
    parser.add_argument('--compress', default=False, action='store_true',
        help='Compress corefile or not.')
    parser.add_argument('--no-convert', action='store_true',
        help='Do not convert checkpoints in the backgroud')
    parser.add_argument('--max-checkpoints', '-m', default=-1, type=int,
        help='Create a maximum number of checkpoints. -1 for unlimited')
    parser.add_argument('--debug-mode', default=False, action='store_true',
        help='For debugging program execution, run IPython after checkpointing.')
    parser.add_argument('--directory', '-d', default='.',
        help='The parent directory of the output checkpoint directories.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--stepi', '-s', nargs='?', type=int,
        help=('Rather than stepping by time, '
          'create checkpoints by number of instructions.'))
    group.add_argument('--interval', type=float, default=1.0,
        help='How often to stop and take a checkpoint.')
    group.add_argument('--breakpoints', type=str, nargs='*',
        help=('Break at certain locations within the program. At these points,'
              ' the program will break into a GDB-enabled shell.'))


def gdb_main():
    checkpoint_root_dir = str(os.environ['CHECKPOINT_ROOT_DIR'])
    max_checkpoints     = int(os.environ['CHECKPOINT_MAXIMUM'])
    debug_mode          = os.environ['CHECKPOINT_DEBUG'] == 'True'
    compress_core_files = os.environ['CHECKPOINT_COMPRESS'] == 'True'
    convert_checkpoints = os.environ['CHECKPOINT_CONVERT'] == 'True'

    engine = GDBEngine(checkpoint_root_dir, compress_core_files,
                       convert_checkpoints)

    if 'CHECKPOINT_INTERVAL' in os.environ:
        checkpoint_interval = float(os.environ['CHECKPOINT_INTERVAL'])
        engine.run_time(checkpoint_interval, max_checkpoints, debug_mode)
    elif 'CHECKPOINT_INSTS' in os.environ:
        checkpoint_instructions = int(os.environ['CHECKPOINT_INSTS'])
        engine.run_inst(checkpoint_instructions, max_checkpoints, debug_mode)
    elif 'CHECKPOINT_LOCS' in os.environ:
        checkpoint_locations = os.environ['CHECKPOINT_LOCS'].split()
        engine.run_interact(checkpoint_locations, debug_mode)

#########################################################################

def add_args(parser):
    LapidaryConfig.add_config_arguments(parser)
    SpecBench.add_parser_args(parser)
    add_arguments(parser)

def main(args):
    #parser = ArgumentParser('Create raw checkpoints of a process through GDB')
    #LapidaryConfig.add_config_arguments(parser)
    #SpecBench.add_parser_args(parser)
    #add_arguments(parser)

    #args = parser.parse_args()
    config = LapidaryConfig.get_config(args)

    ld_path = None
    if 'libc_path' in config:
        ld_sos = glob.glob(f"{config['libc_path']}/lib/ld*.so")
        assert len(ld_sos) == 1
        ld_path = ld_sos[0]

    SpecBench.maybe_display_spec_info(args)

    if args.cmd and args.bench:
        raise Exception('Can only pick one!')

    arg_list = []
    gdbprocs = []
    if args.cmd:
        if ld_path is not None:
            bin_name = args.cmd[0]
            new_bin  = bin_name + '.mod'
            if not Path(new_bin).exists():
                shutil.copyfile(bin_name, new_bin)
                shutil.copymode(bin_name, new_bin)
                cmdstr = f'patchelf --set-interpreter {ld_path} {new_bin}'
                subprocess.check_call(shlex.split(cmdstr))
            
            args.cmd[0] = new_bin

        arg_list = args.cmd
        print(arg_list)
        print(config)
        gdbproc = GDBProcess(arg_list,
                             checkpoint_interval=args.interval,
                             checkpoint_instructions=args.stepi,
                             checkpoint_locations=args.breakpoints,
                             max_checkpoints=args.max_checkpoints,
                             root_dir=args.directory,
                             compress=args.compress,
                             convert=not args.no_convert,
                             debug_mode=args.debug_mode)
        gdbprocs = [gdbproc]
    else:
        benchmarks = SpecBench.get_benchmarks(args)
        for benchmark in benchmarks:
            print('Setting up process for {}...'.format(benchmark))
            bench = SpecBench(config).create(args.suite, benchmark, args.input_type)
            arg_list = [str(bench.binary)] + bench.args

            gdbproc = GDBProcess(arg_list,
                                 checkpoint_interval=args.interval,
                                 checkpoint_instructions=args.stepi,
                                 checkpoint_locations=args.breakpoints,
                                 max_checkpoints=args.max_checkpoints,
                                 root_dir=args.directory,
                                 compress=args.compress,
                                 convert=not args.no_convert,
                                 debug_mode=args.debug_mode)
            gdbprocs += [gdbproc]

    for gdbproc in gdbprocs:
        gdbproc.run()

if __name__ == '__main__':
    try:
        import gdb
        gdb.execute('help', to_string=True)
    except (ImportError, AttributeError) as e:
        main()
    else:
        gdb_main()
