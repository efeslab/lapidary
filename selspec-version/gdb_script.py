#! /usr/bin/env python3

from argparse import ArgumentParser
from threading import Timer
from multiprocessing import Process
from time import sleep
import os
import signal

import gdb

def control_c(pid, seconds):
    print('Will interrupt gdb at {} from {} in {} seconds'.format(
      pid, os.getpid(), seconds))
    sleep(seconds)
    print('Now!')
    os.kill(pid, signal.SIGINT)

def dump_core(filename):
    gdb.execute('gcore {}'.format(filename))

def run_with_gdb(binary, args):
    gdb.execute('set auto-load safe-path /')
    gdb.execute('exec-file {}'.format(binary))

    pid = os.getpid()
    proc = Process(target=control_c, args=(pid, 4))
    proc.start()

    gdb.execute('run {}'.format(' '.join(args)))
    proc.join()

    dump_core('outfile.core')

def exit_gdb():
    gdb.execute('set confirm off')
    gdb.execute('quit')

def main():
    parser = ArgumentParser(description='Play around with the GDB library')

    parser.add_argument('binary', help='Command to run')
    parser.add_argument('args', help='Arguments to pass to command', nargs='*')

    args = parser.parse_args()
    print('Run {} with args={}'.format(args.binary, args.args))
    run_with_gdb(args.binary, args.args)
    print('Ran example, now quitting')
    exit_gdb()

if __name__ == '__main__':
    gdb.execute('print $args')
    args = gdb.history(0).string().split(' ')

    import sys
    sys.argv += args
    main()
else:
    print(__name__)
