from pathlib import Path
import json
import gzip
from elftools.elf.elffile import ELFFile

class GDBCheckpoint:

    MAPPINGS_JSON = 'mappings.json'
    GDB_CORE_FILE = 'gdb.core'
    GDB_GZIP_FILE = 'gdb.core.gz'
    PMEM_FILE     = 'system.physmem.store0.pmem'

    def __init__(self, checkpoint_directory):
        assert isinstance(checkpoint_directory, Path)
        self.checkpoint_directory = checkpoint_directory

        self.mappings_file = self.checkpoint_directory / self.MAPPINGS_JSON
        self.gdb_core_file = self.checkpoint_directory / self.GDB_CORE_FILE
        self.gdb_gzip_file = self.checkpoint_directory / self.GDB_GZIP_FILE
        self.pmem_file     = self.checkpoint_directory / self.PMEM_FILE
        self.mappings      = None

    def get_mappings(self):
        if self.mappings is None:
            with self.mappings_file.open() as f:
                mappings = json.load(f)
                self.mappings = {}
                for key, mapping in mappings.items():
                    if key == 'mem_size':
                        self.mappings[key] = mapping
                    else:
                        self.mappings[int(key)] = mapping
        return self.mappings

    def is_valid_checkpoint(self):
        exists = self.mappings_file.exists() and \
            (self.gdb_core_file.exists or self.gdb_gzip_file.exists())
        valid = True
        if exists:
            try:
                with self.get_core_file_handle() as core:
                    core_elf = ELFFile(core)
            except:
                valid = False
        return exists and valid

    def get_core_file_handle(self):
        if self.gdb_core_file.exists():
            return self.gdb_core_file.open('rb')
        return gzip.open(str(self.gdb_gzip_file), 'rb')

    def get_pmem_file_handle(self):
        return self.pmem_file.open('wb')

    def pmem_file_exists(self):
        return self.pmem_file.exists()

    def __str__(self):
        return str(self.checkpoint_directory)


class Gem5Checkpoint(GDBCheckpoint):
    def is_valid_checkpoint(self):
        return super().is_valid_checkpoint(self) and self.pmem_file.exists()

class Gem5DiffCheckpoint(GDBCheckpoint):
    
    def __init__(self, checkpoint_directory):
        super().__init__(self, checkpoint_directory)
        self.pmem_diff_file = self.pmem_file + '.diff'
    
    def is_valid_checkpoint(self):
        return super().is_valid_checkpoint(self) and self.pmem_diff_file.exists()
