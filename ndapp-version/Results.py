#! /usr/bin/env python3
from argparse import ArgumentParser
from collections import defaultdict
from IPython import embed
import itertools
import json
from enum import Enum
from math import sqrt
import pandas as pd
from pathlib import Path
from pprint import pprint
import re

import Utils
from SpecBench import *
from Graph import Grapher

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)
#pd.set_option('display.max_rows', None)

class RunType(Enum):
    IN_ORDER      = 'in-order'
    OUT_OF_ORDER  = 'out-of-order'
    COOLDOWN      = 'cooldown'

class Results:

    INST_TYPES = [
        "Miscellaneous",
        #"Nop",
        "Integer",
        "Floating",
        #"CC",
        #"Vector",
        "Load",
        "Store",
        "DirectCondCtrl",
        "DirectUncondCtrl",
        "IndirectCondCtrl",
        "IndirectUncondCtrl",
        "Call",
        "Return",
    ]

    KRL_O3_ADDED_STATS = ['avgLatencyToIssue_{}'.format(i) for i in INST_TYPES]

    O3_STAT_NAMES = [ 'sim_insts',
                      'sim_ops',
                      'sim_ticks',
                      'system.cpu.fetch.fetchedDirectBranches',
                      'system.cpu.fetch.Branches',
                      'cpi',
                      'ipc',
                      'avgROBSize',
                      'avgLatencyToIssue',
                      'system.cpu.icache.numBlocksInitialized',
                      'system.l2.numBlocksInitialized',
                      'system.cpu.dcache.numBlocksInitialized',
                      'system.cpu.icache.overall_misses::total',
                      'system.cpu.dcache.overall_misses::total',
                      'system.l2.overall_misses::total',
                      # 'system.cpu.rob.latencyToIssue_totalCycles',
                      # 'system.cpu.rob.latencyToIssue_numInstructions',
                      # 'system.cpu.commit.commitCyclesBreakDown',
                      'system.cpu.rob.robNumEntries_accumulator',
                      # 'system.cpu.branchPred.indirect',
                      'system.cpu.branchPred.BTB',
                      '.icache.cacheMisses::R',
                      '.dcache.cacheMisses::R',
                      '.l2.cacheMisses::R',
                      # '.outstandingMemOperations::',
                      'MLP',
                    ] + KRL_O3_ADDED_STATS

    IN_ORDER_STAT_NAMES = ['sim_insts', 'sim_ticks', 'cpi', 'ipc']

    def __init__(self, runtype, benchmark_name, stats_file, config_name):
        assert isinstance(runtype, RunType)
        assert isinstance(benchmark_name, str)
        assert isinstance(stats_file, Utils.StatsFile)
        if runtype == RunType.IN_ORDER:
            self.in_order = True
        else:
            self.in_order = False
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

        if not self.in_order:
            try:
                robNumEntriesAccumulator = \
                        self.final_stats['system.cpu.rob.robNumEntries_accumulator']
                latencyToIssue_cycles    = \
                        self.final_stats['system.cpu.rob.latencyToIssue_totalCycles']
                self.final_stats['avgLatencyToIssue'] = \
                                                 float(latencyToIssue_cycles) / float(micro_ops)

                # START KRL
                #print('avgLatencyToIssue: {}'.format(self.final_stats['avgLatencyToIssue']))

                for inst_type in INST_TYPES:
                    inst_type_total_cycles =  self.final_stats['system.cpu.rob.latenciesToIssue_totalCycles::' + inst_type]
                    inst_type_num_insts = self.final_stats['system.cpu.rob.latenciesToIssue_numInstructions::' + inst_type]
                    if inst_type_num_insts > 0:
                        self.final_stats['avgLatencyToIssue_' + inst_type] = \
                            float(inst_type_total_cycles) / float(inst_type_num_insts)
                    else:
                        self.final_stats['avgLatencyToIssue_' + inst_type] = 0.0

                    #print('\t' + inst_type + ': {}'.format(self.final_stats['avgLatencyToIssue_' + inst_type]))
                # END KRL

                self.final_stats['avgROBSize'] = float(robNumEntriesAccumulator) / float(cycles)
                self.final_stats['MLP' ] = self.calcMLP()
            except KeyError as e:
                print('KeyError: {}'.format(e))

    def stats(self):
        if len(self.final_stats) == 0:
            raise Exception('Trying to inspect stats before initialization!')
        return self.final_stats

    def human_stats(self):
        stats = Results.O3_STAT_NAMES
        if self.in_order:
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

