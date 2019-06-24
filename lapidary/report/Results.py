from IPython import embed
from argparse import ArgumentParser
from collections import defaultdict
from enum import Enum
from math import sqrt
from pathlib import Path
from pprint import pprint
import itertools
import json
import pandas as pd
import re

from lapidary.utils import *
from lapidary.config.specbench.SpecBench import *
#from lapidary.Graph import Grapher

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)
#pd.set_option('display.max_rows', None)

class RunType(Enum):
    IN_ORDER      = 'in-order'
    OUT_OF_ORDER  = 'out-of-order'
    COOLDOWN      = 'cooldown'
    INVISISPEC    = 'invisispec'

class Results:
    O3_STAT_NAMES = [ 'sim_insts',
                      'sim_ops',
                      'sim_ticks',
                      'system.cpu.fetch.fetchedDirectBranches',
                      'system.cpu.fetch.Branches',
                      'cpi',
                      'ipc',
                      'avgROBSize',
                      'avgLatencyToIssue',
                      # 'system.cpu.icache.numBlocksInitialized',
                      # 'system.l2.numBlocksInitialized',
                      # 'system.cpu.dcache.numBlocksInitialized',
                      # 'system.cpu.icache.overall_misses::total',
                      # 'system.cpu.dcache.overall_misses::total',
                      # 'system.l2.overall_misses::total',
                      # 'system.cpu.rob.latencyToIssue_totalCycles',
                      # 'system.cpu.rob.latencyToIssue_numInstructions',
                      # 'system.cpu.commit.commitCyclesBreakDown',
                      'system.cpu.rob.robNumEntries_accumulator',
                      # 'system.cpu.branchPred.indirect',
                      # 'system.cpu.branchPred.BTB',
                      # '.icache.cacheMisses::R',
                      # '.dcache.cacheMisses::R',
                      # '.l2.cacheMisses::R',
                      # '.outstandingMemOperations::',
                      'MLP',
                      'system.cpu.commit.commitCyclesBreakDown::GeneralStall',
                      'system.cpu.commit.commitCyclesBreakDown::InstructionFault',
                      'system.cpu.commit.commitCyclesBreakDown::LoadStall',
                      'system.cpu.commit.commitCyclesBreakDown::StoreStall',
                      'system.cpu.commit.commitCyclesBreakDown::LoadOrder',
                      'system.cpu.commit.commitCyclesBreakDown::StoreOrder',
                      'system.cpu.commit.commitCyclesBreakDown::MemBarrier',
                      'system.cpu.commit.commitCyclesBreakDown::WriteBarrier',
                      'system.cpu.commit.commitCyclesBreakDown::SquashingBranchMispredict',
                      'system.cpu.commit.commitCyclesBreakDown::SquashingMemoryViolation',
                      'system.cpu.commit.commitCyclesBreakDown::RetiringSquashes',
                      'system.cpu.commit.commitCyclesBreakDown::CommitSuccess',
                      'system.cpu.commit.commitCyclesBreakDown::ROBEmpty',
                      'system.cpu.commit.commitCyclesBreakDown::total',
                    ]

    IN_ORDER_STAT_NAMES = ['sim_insts', 'sim_ticks', 'cpi', 'ipc', 'MLP']

    def __init__(self, runtype, benchmark_name, stats_file, config_name):
        assert isinstance(runtype, RunType)
        assert isinstance(benchmark_name, str)
        assert isinstance(stats_file, StatsFile)
        if runtype == RunType.IN_ORDER or runtype == RunType.INVISISPEC:
            self.use_in_order_stats = True
        else:
            self.use_in_order_stats = False
        self.stats_file = stats_file
        self.warmup_stats = None
        self.final_stats = None

    def _get_stats(self):
        raw_stats = pd.Series(self.stats_file.get_current_stats())
        return pd.to_numeric(raw_stats, errors='coerce')

    def get_warmup_stats(self):
        self.warmup_stats = self._get_stats()

    def calcMLP(self):
        accumulator = 0
        numCyclesWithAtLeastSingleOutstandingMemOp = 0

        for k,v in self.final_stats.items():
            if 'outstandingMemOperations::' in k and 'total' not in k:
                bucketIndex = float(k.split('::')[1])
                if bucketIndex == 0:
                    continue
                numItems    = v
                accumulator += bucketIndex * numItems
                numCyclesWithAtLeastSingleOutstandingMemOp += numItems

        if numCyclesWithAtLeastSingleOutstandingMemOp == 0:
            return 1.0 # The minium MLP is always 1.

        return accumulator / numCyclesWithAtLeastSingleOutstandingMemOp

    def get_final_stats(self):
        run_stats = self._get_stats()
        assert len(run_stats)

        self.final_stats = run_stats - self.warmup_stats

        # add IPC
        cycles                  = self.final_stats['sim_ticks'] / 500
        insts                   = self.final_stats['sim_insts']
        micro_ops               = self.final_stats[ 'sim_ops' ]
        self.final_stats['ipc'] = float(insts) / float(cycles)
        self.final_stats['cpi'] = float(cycles) / float(insts)

        self.final_stats['version'] = 1.0

        if not self.use_in_order_stats:
            try:
                robNumEntriesAccumulator = \
                        self.final_stats['system.cpu.rob.robNumEntries_accumulator']
                latencyToIssue_cycles    = \
                        self.final_stats['system.cpu.rob.latencyToIssue_totalCycles']
                self.final_stats['avgLatencyToIssue'] = \
                                                 float(latencyToIssue_cycles) / float(micro_ops)
                self.final_stats['avgROBSize'] = float(robNumEntriesAccumulator) / float(cycles)
                self.final_stats['MLP'] = self.calcMLP()
            except KeyError as e:
                print('KeyError: {}'.format(e))

    def stats(self):
        if len(self.final_stats) == 0:
            raise Exception('Trying to inspect stats before initialization!')
        return self.final_stats

    def human_stats(self):
        stats = Results.O3_STAT_NAMES
        if self.use_in_order_stats:
            stats = Results.IN_ORDER_STAT_NAMES

        output = pd.Series(self.final_stats)
        display = pd.Series()

        for requested_stat in stats:
            display = display.append(output.filter(like=requested_stat))

        return display

    def dump_stats_to_file(self, file_path):
        assert isinstance(file_path, Path)
        with file_path.open('w') as f:
            json_str      = self.stats().to_json()
            json_obj      = json.loads(json_str.encode())
            formatted_str = json.dumps(json_obj, indent=4)
            f.write(unicode(formatted_str))

