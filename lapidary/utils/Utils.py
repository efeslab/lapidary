import json
from pathlib import Path
from pprint import pprint
import re
from time import sleep

class StatsFile:
    def __init__(self, file_path):
        self.current_offset = 0
        self.file_size = 0
        self.file_path = file_path
        self.cached_stats = {}

    def __del__(self):
        '''
            The accumulated stats file can actually get quite large, since we 
            just dump the file several hundred times as we count instructions.
            This will ensure it doesn't linger and absorb the entire disk.
        '''
        if self.file_path.exists():
            self.file_path.unlink()

    def get_current_stats(self):
        import m5
        stats = {}
        m5.stats.dump()
        size = self.file_path.stat().st_size
        if self.file_size == size:
            return self.cached_stats

        self.file_size = size
        with self.file_path.open() as fd:
            fd.seek(self.current_offset)
            for line in fd:
                if '--------' in line or len(line.strip()) == 0:
                    continue
                pieces = [x for x in line.split(' ') if len(x.strip()) > 0]
                if len(pieces) > 1:
                    key = pieces[0].strip()
                    val = pieces[1].strip()
                    stats[key] = val

            self.current_offset = fd.tell()
        self.cached_stats = stats
        return stats

def parse_perf_output_insts(stderr_str):
    inst_pattern = re.compile('([0-9\,]+)\s*instructions')

    for line in stderr_str.split('\n'):
        line = line.strip()
        matches = inst_pattern.match(line)
        if matches is not None:
            return int(matches.group(1).replace(',',''))

def get_num_insts_perf(cmd):
    from subprocess import run, PIPE
    if type(cmd) == str:
        cmd = [cmd]
    perf = ['perf', 'stat', '-e', 'instructions']
    proc = run(perf + cmd, stdout=PIPE, stderr=PIPE)
    return parse_perf_output_insts(proc.stderr.decode('ascii'))

def get_num_insts_perf_from_pid(pid):
    from subprocess import Popen, PIPE
    perf = ['perf', 'stat', '-e', 'instructions', '-p', str(pid)]
    proc = Popen(perf, stdout=PIPE, stderr=PIPE)
    sleep(timeout)
    proc.terminate()
    proc.wait()
    return parse_perf_output_insts(proc.stderr.decode('ascii'))

def parse_mem_size_string(mem_size_str):
    mem_pattern = re.compile(r'([0-9]+)([kmgKMG][bB])?')

    matches = mem_pattern.match(mem_size_str)
    if not matches:
        raise Exception('{} is not a valid memory size!'.format(mem_size_str))

    mem_size = int(matches.group(1))
    try:
        size_modifier = matches.group(2).lower()
        if 'kb' in size_modifier:
            mem_size *= 1024
        if 'mb' in size_modifier:
            mem_size *= (1024 ** 2)
        if 'gb' in size_modifier:
            mem_size *= (1024 ** 3)
    except:
        pass

    return mem_size

def select_at_random(list_of_things, num_to_select):
    import random
    return random.sample(list_of_things, num_to_select)

def select_evenly_spaced(list_or_dict, num_to_select):
    from natsort import natsorted, ns
    from copy import copy
    if num_to_select > len(list_or_dict):
        return copy(list_or_dict)

    sorted_keys = natsorted(list_or_dict, alg=ns.IGNORECASE)
    # https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm
    f = lambda m, n: [i*n//m + n//(2*m) for i in range(m)]
    indices = f(num_to_select, len(sorted_keys))
    sublist = [ sorted_keys[i] for i in indices ]

    if isinstance(list_or_dict, list):
        return sublist

    return { k: list_or_dict[k] for k in sublist }

def get_mem_size_from_mappings_file(mappings_file):
    assert isinstance(mappings_file, Path)
    with mappings_file.open() as f:
        mappings = json.load(f)
        return mappings['mem_size']

def get_directory_entries_by_time(directory_path):
    from natsort import natsorted
    assert isinstance(directory_path, Path)
    get_name = lambda d: str(d.name)
    return natsorted(directory_path.iterdir(), key=get_name)


def _get_msr(identifier):
    import ctypes
    libc = ctypes.CDLL(None)
    syscall = libc.syscall
    SYS_arch_prctl = 158
    ret_val = ctypes.c_uint64()
    syscall(SYS_arch_prctl, identifier, ctypes.pointer(ret_val))
    return ret_val.value

def get_fs_base():
    ARCH_GET_FS = 0x1003
    return _get_msr(ARCH_GET_FS)

def get_gs_base():
    ARCH_GET_GS = 0x1004
    return _get_msr(ARCH_GET_GS)
