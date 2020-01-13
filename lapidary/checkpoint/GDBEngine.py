import gzip, json, os, re, resource, signal, shutil, subprocess, sys, logging

from argparse import ArgumentParser
from elftools.elf.elffile import ELFFile
from multiprocessing import Process
from pathlib import Path
from pprint import pprint
from subprocess import Popen, TimeoutExpired
from tempfile import NamedTemporaryFile
from time import sleep

# WORK_DIR = os.path.dirname(__file__)
# if len( WORK_DIR ) == 0:
#     WORK_DIR = "."
# sys.path.append( WORK_DIR )

try:
    from lapidary.config.specbench.SpecBench import *
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from lapidary.config.specbench.SpecBench import *

import lapidary.pypatch
from lapidary.checkpoint.Checkpoints import GDBCheckpoint
from lapidary.checkpoint.CheckpointTemplate import *
from lapidary.checkpoint import CheckpointConvert
from lapidary.config import LapidaryConfig

GLIBC_PATH = Path('../libc/glibc/build/install/lib').resolve()
LD_LIBRARY_PATH_STR = '{}:/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu'.format(GLIBC_PATH)

class GDBEngine:
    ''' This class is used by the gdb process running inside gdb.'''

    # start-address end-address size offset name
    VADDR_REGEX_STRING = r'\s*(0x[0-9a-f]+)\s+0x[0-9a-f]+\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s*(.*)'
    VADDR_REGEX = re.compile(VADDR_REGEX_STRING)

    BAD_MEM_REGIONS = ['[vvar]', '[vsyscall]']

    SIGNAL = signal.SIGINT

    def __init__(self,
                 checkpoint_root_dir,
                 compress_core_files,
                 convert_checkpoints):
        '''
            checkpoint_root_dir: Where to create the checkpoint directory.
            compress_core_files: Whether or not to gzip the memory images.
            convert_checkpoints:
        '''
        from lapidary.checkpoint.GDBShell import GDBShell
        import gdb
        self.shell = GDBShell(self)
        self.chk_num = 0
        self.compress_core_files = compress_core_files
        self.compress_processes  = {}
        self.convert_checkpoints = convert_checkpoints
        self.convert_processes   = {}
        self.logger              = logging.getLogger(name=__name__)

        # Otherwise long arg strings get mutilated with '...'
        gdb.execute('set print elements 0')
        gdb.execute('set follow-fork-mode child')
        args = (gdb.execute('print $args', to_string=True)).split(' ')[2:]
        args = [ x.replace('"','').replace(os.linesep, '') for x in args ]
        assert len(args) > 0
        self.binary = args[0]
        self.args = ' '.join(args[1:])
        if checkpoint_root_dir is not None:
            self.chk_out_dir = Path(checkpoint_root_dir) / \
                '{}_gdb_checkpoints'.format(Path(self.binary).name)
        else:
            self.chk_out_dir = Path( WORK_DIR ) / Path('{}_gdb_checkpoints'.format(Path(self.binary).name))
        gdb.execute('set print elements 200')


    @classmethod
    def _get_virtual_addresses(cls):
        import gdb
        vaddrs = [0]
        sizes = [resource.getpagesize()]
        offsets = [0]
        names = ['null']
        raw_mappings = gdb.execute('info proc mappings', to_string=True)

        for entry in raw_mappings.split(os.linesep):
            matches = cls.VADDR_REGEX.match(entry.strip())
            if matches:
                vaddrs   += [int(matches.group(1), 16)]
                sizes    += [int(matches.group(2), 16)]
                offsets  += [int(matches.group(3), 16)]
                names    += [str(matches.group(4)).strip()]

        return vaddrs, sizes, offsets, names

    @classmethod
    def _get_memory_regions(cls):
        vaddrs, sizes, offsets, names = cls._get_virtual_addresses()
        paddrs = []
        flags = []
        next_paddr = 0
        for vaddr, size in zip(vaddrs, sizes):
            paddrs += [next_paddr]
            flags += [0]
            next_paddr += size

        return paddrs, vaddrs, sizes, offsets, flags, names

    @classmethod
    def _create_mappings(cls, filter_bad_regions=False, expand=False):
        paddrs, vaddrs, sizes, offsets, flags, names = cls._get_memory_regions()
        assert len(paddrs) == len(vaddrs)
        assert len(paddrs) == len(sizes)
        assert len(paddrs) == len(flags)
        assert len(paddrs) == len(names)
        mappings = {}
        index = 0
        pgsize = resource.getpagesize()
        for p, v, s, o, f, name in zip(paddrs, vaddrs, sizes, offsets, flags, names):
            # if filter_bad_regions and name in GDBEngine.BAD_MEM_REGIONS:
            #     print('Skipping region "{}" (v{}->v{}, p{}->p{})'.format(name,
            #       hex(v), hex(v + s), hex(p), hex(p + s)))
            #     continue
            if expand:
                # print( "Expanding v = 0x%x" % (v) )
                for off in range(0, s, pgsize):
                    paddr = p + off if p != 0 else 0
                    vaddr = v + off
                    offset = o + off
                    mappings[vaddr] = MemoryMapping(
                        index, paddr, vaddr, pgsize, offset, f, name)
            else:
                mappings[v] = MemoryMapping(index, p, v, s, o, f, name)

            index += 1

        return mappings

    @staticmethod
    def _create_convert_process(checkpoint_dir):
        gdb_checkpoint = GDBCheckpoint(checkpoint_dir)
        proc = Process(target=CheckpointConvert.convert_checkpoint,
                       args=(gdb_checkpoint, True))
        proc.start()
        return proc

    def _dump_core_to_file(self, file_path):
        import gdb
        gdb.execute('set use-coredump-filter off')
        gdb.execute('set dump-excluded-mappings on')
        gdb.execute('gcore {}'.format(str(file_path)))
        if self.compress_core_files:
            print('Creating gzip process for {}'.format(str(file_path)))
            gzip_proc = Popen(['gzip', '-f', str(file_path)])
            self.compress_processes[file_path.parent] = gzip_proc
        elif self.convert_checkpoints:
            print('Creating convert process for {}'.format(str(file_path.parent)))
            convert_proc = GDBEngine._create_convert_process(file_path.parent)
            self.convert_processes[file_path.parent] = convert_proc

    def _dump_mappings_to_file(self, mappings, mem_size, file_path):
        json_mappings = {'mem_size': mem_size}
        for vaddr, mapping in mappings.items():
            json_mappings[vaddr] = mapping.__dict__

        with file_path.open('w') as f:
            json.dump(json_mappings, f, indent=4)


    def _calculate_memory_size(self, mappings):
        mem_size = 0
        for vaddr, mapping in mappings.items():
            mem_size = max(mapping.paddr + mapping.size, mem_size)
        # Avoid OOM errors
        return 2 * mem_size

    def get_mmap_end(self):
        return 18446744073692774400

        # mappings = self._create_mappings()
        # addresses = list(mappings.keys())
        # addresses.sort()

        # mmap_end = None
        # for i in range( len(addresses) ):
        #     currentMap = mappings[ addresses[i] ]
        #     if "[heap]" == currentMap.name:
        #         mmap_end = mappings[ addresses[i+1] ].vaddr

        # if mmap_end is None:
        #     raise Exception( "Could not find mmap_end" )

        # print( "mmapEnd is 0x%x" % mmap_end )

        # return mmap_end

    def _create_gem5_checkpoint(self, debug_mode):
        chk_loc = self.chk_out_dir / '{}_check.cpt'.format(self.chk_num)
        if chk_loc.exists():
            self.logger.warning('{} already exists, overwriting.'.format(str(chk_loc)))
        else:
            chk_loc.mkdir(parents=True)
        pmem_name = 'system.physmem.store0.pmem'
        chk_file = 'm5.cpt'

        template_mappings = self._create_mappings(True, expand=True)
        regs = RegisterValues(self.fs_base)

        total_mem_size = self._calculate_memory_size(template_mappings)

        file_mappings = self._create_mappings(True)

        stack_mapping = [ m for v, m in file_mappings.items() if 'stack' in m.name ]
        assert len(stack_mapping) == 1
        stack_mapping = stack_mapping[0]

        fill_checkpoint_template(
            output_file=str(chk_loc / chk_file),
            mappings=template_mappings,
            misc_reg_string=regs.get_misc_reg_string(),
            int_reg_string=regs.get_int_reg_string(),
            pc_string=regs.get_pc_string(),
            next_pc_string=regs.get_next_pc_string(),
            float_reg_string=regs.get_float_reg_string(),
            mem_size=total_mem_size,
            stack_mapping=stack_mapping,
            brk=self._get_brk_value(),
            mmap_end = self.get_mmap_end())

        self._dump_core_to_file(chk_loc / 'gdb.core')
        self._dump_mappings_to_file(file_mappings, total_mem_size,
            chk_loc / 'mappings.json')
        self.chk_num += 1

        if debug_mode:
            self.logger.info("Entering IPython shell for debug mode.")
            import IPython
            IPython.embed()

    @classmethod
    def _interrupt_in(cls, sec):
        '''
            Used to pause GDB with running in timed mode so that checkpoints 
            can be made. A little hackish, but it works.

            The idea is, when the inferior process gets an interrupt, control
            is given back to the debugger.
        '''
        import gdb
        def control_c(pid, seconds):
            sleep(seconds)
            os.kill(pid, cls.SIGNAL)

        ipid = gdb.selected_inferior().pid
        proc = Process(target=control_c, args=(ipid, sec))
        proc.start()
        return proc


    def _can_create_valid_checkpoint(self):
        mappings = self._create_mappings()
        regs = RegisterValues(self.fs_base)

        current_pc = int(regs.get_pc_string())
        for vaddr, mapping in mappings.items():
            if current_pc in mapping and mapping.name in GDBEngine.BAD_MEM_REGIONS:
                self.logger.debug('Skipping checkpoint at {} since it is in {} region'.format(
                      hex(current_pc), mapping.name))
                return False

        return True

    @staticmethod
    def _get_current_language():
        '''
            We have some C files we want to compile. However, this doesn't 
            work if we're getting checkpoints for a fortran benchmark. So, we
            need to retrieve the original language so we can change it to C
            temporarily for our purposes. We promise we'll set it back as soon
            as we're done.
        '''
        import gdb
        lang_raw = gdb.execute('show language', to_string=True)

        lang = lang_raw.split()[-1].split('"')[0]
        if not lang:
            lang = lang_raw.split('"')[1]
        if not lang:
            raise gdb.error('"show language" command returned nothing! Raw: ',
                gdb.execute('show language', to_string=True))
        
        return lang


    def _get_brk_value(self):
        '''
            Here we have to compile the get_brk program, which is injected into
            the running binary so that it can make a syscall to retrieve the 
            brk value.

            Credit to Ofir Weisse for this particular bit.
        '''
        import struct, gdb

        orig_lang = self._get_current_language()
            
        gdb.execute('set language c')

        brk_file = Path('/tmp/sbrk.txt' )
        if os.path.exists( brk_file ):
            os.remove( brk_file )

        gdb.execute('compile file -raw %s/get_brk.c' % WORK_DIR )
        brk = 0
        self.logger.debug( "#"* 20 + "cwd = %s" % os.getcwd() )
        try:
            with brk_file.open('rb') as f:
                data = f.read()[:8]
                self.logger.debug(data)
                self.logger.debug(struct.unpack('Q', data))
                brk = struct.unpack('Q', data)[0]
        except:
            pass
        finally:
            brk_file.unlink()
        
        gdb.execute('set language {}'.format(orig_lang))
        self.logger.info('Found brk: {} ({})'.format(brk, hex(brk)))
        return brk


    def _get_fs_base(self):
        import struct, gdb
        orig_lang = self._get_current_language()
        gdb.execute('set language c')
        gdb.execute('compile file -raw %s/get_fs_base.c' % WORK_DIR )
        fs_base = 0
        fs_base_file = Path('/tmp/fs_base.txt')
        try:
            with fs_base_file.open('rb') as f:
                data = f.read()[:8]
                self.logger.debug(data)
                self.logger.debug(struct.unpack('Q', data))
                fs_base = struct.unpack('Q', data)[0]
        except:
            pass
        finally:
            fs_base_file.unlink()
        
        gdb.execute('set language {}'.format(orig_lang))
        self.logger.debug('Found FS BASE: {} ({})'.format(fs_base, hex(fs_base)))
        return fs_base

    def _run_base(self, debug_mode):
        '''
            Used by all main run methods for process setup. Breaks at main and
            fast-forwards until that point to avoid profiling glibc startup.
        '''

        import gdb
        gdb.execute('set auto-load safe-path /')
        gdb.execute('exec-file {}'.format(self.binary))
        gdb.execute('file {}'.format(self.binary))

        gdb.execute('break main')
        self.logger.info('Running with args: "{}"'.format(self.args))

        gdb.execute('run {}'.format(self.args))
        self.fs_base = self._get_fs_base()
        if debug_mode:
            self.logger.info("Entering IPython shell for debug mode.")
            import IPython
            IPython.embed()


    def _poll_background_processes(self, wait=False):
        '''
            Check on that status of background threads which are processing 
            checkpoint files.

            wait: Whether or not to stall until all processes are complete,
            default is false.
        '''

        timeout = 0.001
        if wait:
            self.logger.info('Waiting for background processes to complete before exit.')
            timeout = None
        gzip_complete = []
        for file_path, gzip_proc in self.compress_processes.items():
            gzip_proc.join(timeout)
            if not gzip_proc.is_alive():
                gzip_complete += [file_path]
                if self.convert_checkpoints:
                    self.logger.info('Creating convert process for {} after gzip'.format(
                        str(file_path)))
                    convert_proc = GDBEngine._create_convert_process(file_path)
                    self.convert_processes[file_path.parent] = convert_proc
        for key in gzip_complete:
            self.logger.info('Background gzip for {} completed'.format(key))
            self.compress_processes.pop(key)

        convert_complete = []
        for file_path, convert_proc in self.convert_processes.items():
            convert_proc.join(timeout)
            if not convert_proc.is_alive():
                convert_complete += [file_path]
        for key in convert_complete:
            self.logger.info('Background convert for {} completed'.format(key))
            self.convert_processes.pop(key)

    def _try_create_checkpoint(self, debug_mode):
        '''
            Attempt to create a checkpoint.
        '''

        self._poll_background_processes()

        if self._can_create_valid_checkpoint():
            self.logger.info('Creating checkpoint #{}'.format(self.chk_num))
            self._create_gem5_checkpoint(debug_mode)


    def run_time(self, sec_between_chk, max_iter, keyframes, debug_mode):
        '''
            Main method for generating checkpoints every N seconds.
        '''

        import gdb
        self.logger.info('Running with {} seconds between checkpoints.'.format(
          sec_between_chk))
        self._run_base(debug_mode)

        while max_iter < 0 or self.chk_num < max_iter:
            try:
                proc = self._interrupt_in(sec_between_chk)
                gdb.execute('continue')
                proc.join()
                self._try_create_checkpoint(debug_mode)
                self.logger.info('Checkpoint {} has been created, continuing.'.format(self.chk_num))
            except (gdb.error, KeyboardInterrupt) as e:
                self.logger.error(e)
                break
        
        self._poll_background_processes(True)


    def run_inst(self, insts_between_chk, max_iter, keyframes, debug_mode):
        '''
            Main method for generating checkpoints every N instructions.
            Not recommended, as stepping by number of instructions is precise,
            yet very slow.
        '''

        import gdb
        print('Running with {} instructions between checkpoints.'.format(
          insts_between_chk))
        self._run_base(debug_mode)

        while max_iter < 0 or self.chk_num < max_iter:
            try:
                gdb.execute('stepi {}'.format(insts_between_chk))
                self._try_create_checkpoint(debug_mode)
            except (gdb.error, KeyboardInterrupt) as e:
                break
        
        self._poll_background_processes(True)


    def run_interact(self, breakpoints, debug_mode):
        '''
            Main method for running the checkpoint engine in interactive mode.
            This invokes the GDBShell and allows for manual checkpoint creation
            and general process inspection.
        '''

        import gdb
        print('Running with {} breakpoints.'.format(len(breakpoints)))
        for breakpoint in breakpoints:
            gdb.execute('set breakpoint pending on')
            gdb.execute('break {}'.format(breakpoint))

        self._run_base(debug_mode)

        while True:
            try:
                self.shell.cmdloop()
                gdb.execute('continue')
            except (gdb.error, KeyboardInterrupt) as e:
                break
        
        self._poll_background_processes(True)
