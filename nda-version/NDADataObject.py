from argparse import ArgumentParser
from collections import defaultdict
import copy
from IPython import embed
import itertools
import json
from enum import Enum
from math import sqrt
import pandas as pd
import numpy as np
from pathlib import Path
from pprint import pprint
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
from matplotlib.patches import Patch
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import matplotlib.ticker as ticker
import re
import yaml

import Utils
from SpecBench import *
from Graph import Grapher

import pandas as pd

class NDADataObject:
    def __init__(self, file_path):
        if isinstance(file_path, str):
            file_path = Path(file_path)
        assert isinstance(file_path, Path)
        with file_path.open() as f:
            report_data = json.load(f)
            results_data = report_data['results']

            self.dfs = defaultdict(dict)
            for benchmark, config_data in results_data.items():
                for config_name, raw_df in config_data.items():
                    df = pd.DataFrame(raw_df)
                    self.dfs[benchmark][config_name.lower()] = df

    def _reorder_data_frames(self):
        new_dict = defaultdict(dict)
        for x, x_data in self.dfs.items():
            for y, y_df in x_data.items():
                new_dict[y][x] = y_df

        return new_dict

    def reorder_data_frames(self, dfs):
        new_dict = defaultdict(dict)
        for x, x_data in dfs.items():
            for y, y_df in x_data.items():
                new_dict[y][x] = y_df

        return new_dict

    def data_by_benchmark(self):
        return self.dfs

    def data_by_config(self):
        return self._reorder_data_frames()

    def filter_benchmarks(self, benchmark_filter, dfs):
        if benchmark_filter is None:
            return dfs
        new_dfs = copy.deepcopy(dfs)
        for bench in [k for k in dfs]:
            matches_any = False
            for f in benchmark_filter:
                if f == bench:
                    matches_any = True
                    break
            if not matches_any:
                new_dfs.pop(bench, None)
        return new_dfs

    def filter_configs(self, config_filter, dfs):
        assert config_filter is not None
        new_dfs = copy.deepcopy(dfs)
        for bench in [k for k in dfs]:
            for config in [x for x in dfs[bench]]:
                matches_any = False
                for c in config_filter:
                    if c == config:
                        matches_any = True
                        break
                if not matches_any:
                    new_dfs[bench].pop(config, None)

        return new_dfs


    def filter_stats(self, stat, dfs):
        new_dfs = {}
        for x, x_data in dfs.items():
            per_x = {}
            for y, y_data in x_data.items():
                if stat in y_data:
                    per_x[y] = y_data[stat]

            new_df = pd.DataFrame(per_x).T
            new_dfs[x] = new_df

        return new_dfs

    def filter_stat_field(self, field, dfs):
        new_dfs = {}
        for x, x_df in dfs.items():
            per_x = {}
            for y, y_data in x_df.T.items():
                if field not in y_data:
                    raise Exception('Not available!')
                per_x[y] = y_data[field]

            new_df = pd.Series(per_x)
            new_dfs[x] = new_df

        return pd.DataFrame(new_dfs)

    def average_stats(self, dfs):
        averages = {}
        for x, df in dfs.items():
            averages[x] = df.mean()

        return pd.DataFrame(averages)

    def _get_stat_attribute(self, stat, attr):
        dataframes = self.data_frames

        stat_data = {}
        for bench, config_dict in dataframes.items():
            stats = {}
            for config, df in config_dict.items():
                stats[config] = df[stat][attr]
            per_bench = pd.Series(stats)
            stat_data[bench] = per_bench

        return pd.DataFrame(stat_data)

    def output_text(self):
        dataframes = self.dfs

        cpi_mean  = self._get_stat_attribute('cpi', 'mean')
        cpi_ci    = self._get_stat_attribute('cpi', 'ci')
        cpi_count = self._get_stat_attribute('cpi', 'count')
        cpi_ci_p  = cpi_ci / cpi_mean

        for bench, data in cpi_count.iteritems():
            assert data.min() == data.max()

        for bench, val in cpi_ci_p.max().iteritems():
            if val > 0.05:
                print('\033[91m{0} has CI% > 5%: {1:.1f}%, only {2:.0f} items!\033[0m'.format(
                    bench, val * 100.0, cpi_count.min()[bench]))
                print(cpi_ci_p[bench].to_string(float_format='{:,.1%}'.format))
            else:
                print('\033[92m{0} has CI% <= 5%: {1:.1f}%, with {2:.0f} items!\033[0m'.format(
                    bench, val * 100.0, cpi_count.min()[bench]))

        o3   = 'o3'
        inor = 'inorder'

        print('='*80)
        for bench, data in cpi_mean.iteritems():
            if o3 in data and data[o3] > data.min():
                print('\033[91m{0} has OOO: {1:.3f} > the minimum only {2:.3f}!\033[0m'.format(
                    bench, data[o3], data.min()))
        print('='*80)
        printme = False
        for bench, data in cpi_count.iteritems():
            for config, num in data.iteritems():
                if num < 1.0:
                    printme = True
                    print('\033[91m{}: {} has no results!\033[0m'.format(
                        bench, config))
        print('='*80) if printme else None

        print('Confidence interval range per benchmark:')
        for bench, val in cpi_ci_p.max().iteritems():
            print('Max confidence interval percent for {0}: {1:.1%}'.format(bench, val))
        print('MAX CONFIDENCE INTERVAL PERCENT: {0:.1%}'.format(cpi_ci_p.max().max()))
        print('MAX CONFIDENCE INTERVAL: +/- {0:.1f} CPI'.format(cpi_ci.max().max()))

        p_percent = lambda l, x: print('--- {0}: {1:.1f}%'.format(l, x * 100.0))
        p_times = lambda l, x: print('--- {0}: {1:.1f}X'.format(l, x))
        configs = []
        for bench, data in cpi_mean.iteritems():
            for config, num in data.iteritems():
                configs += [[config, self._get_config_name(config)]]
            break
        for c, name in configs:
            print()
            if o3 in cpi_mean.T:
                print('CPI Percent Slowdown (Overhead) ({})'.format(name))
                slowdown = ((cpi_mean.T[c] - cpi_mean.T[o3]) / cpi_mean.T[o3])
                p_percent('Min', slowdown.min())
                p_percent('Max', slowdown.max())
                p_percent('Mean', slowdown.mean())

            speedup = cpi_mean.T[inor] / (cpi_mean.T[inor] - cpi_mean.T[c])
            print('CPI Percent Speedup ({})'.format(name))
            p_percent('Min', speedup.min())
            p_percent('Max', speedup.max())
            p_percent('Mean', speedup.mean())

            times = cpi_mean.T[inor] / cpi_mean.T[c]
            print('CPI Times Faster ({})'.format(name))
            p_times('Min', times.min())
            p_times('Max', times.max())
            p_times('Mean', times.mean())

            if o3 in cpi_mean.T:
                gap = ((cpi_mean.T[inor] - cpi_mean.T[c]) / (cpi_mean.T[inor] - cpi_mean.T[o3]))
                print('CPI Percent Gap Closed ({})'.format(name))
                p_percent('Min', gap.min())
                p_percent('Max', gap.max())
                p_percent('Mean', gap.mean())

            print('Number of checkpoints ({})'.format(name))
            print('--- Min: {0:.0f}'.format(cpi_count.T[c].min()))
            print('--- Max: {0:.0f}'.format(cpi_count.T[c].max()))
            print('--- Mean: {0:.0f}'.format(cpi_count.T[c].mean()))


    def calculate_cpi_breakdown(self, dfs):
        prefix_fn = lambda s: 'system.cpu.commit.commitCyclesBreakDown::{}'.format(s)
        benchmark_dfs = {}
        for benchmark, config_data in dfs.items():
            baseline_cpi = config_data['o3']['cpi']['mean']

            stat_per_config = defaultdict(dict)
            for config_name, df in config_data.items():

                config_cpi = df['cpi']['mean']
                cpi_ratio  = config_cpi / baseline_cpi

                df = df.fillna(0.0)

                components = []
                if 'inorder' not in config_name and \
                    'invisiblespec' not in config_name and \
                    'invisispec' not in config_name:
                    gen_stalls = (df[prefix_fn('GeneralStall')]     + \
                                  df[prefix_fn('InstructionFault')]).rename('Backend Stalls')
                    mem_stalls = (df[prefix_fn('LoadStall')]    + \
                                  df[prefix_fn('StoreStall')]   + \
                                  df[prefix_fn('LoadOrder')]    + \
                                  df[prefix_fn('StoreOrder')]   + \
                                  df[prefix_fn('MemBarrier')]   + \
                                  df[prefix_fn('WriteBarrier')]).rename('Memory Stalls')
                    squashing  = (df[prefix_fn('SquashingBranchMispredict')] + \
                                  df[prefix_fn('SquashingMemoryViolation')]  + \
                                  df[prefix_fn('RetiringSquashes')]).rename('squashing')
                    commit     = df[prefix_fn('CommitSuccess')].rename('Commit')
                    rob_empty  = df[prefix_fn('ROBEmpty')].rename('rob_empty')
                    total      = df[prefix_fn('total')]
                    other      = (total - (gen_stalls + mem_stalls + \
                                squashing + commit + rob_empty)).rename('other')
                    assert other['mean']/total['mean'] <= 0.01
                    components = [commit, mem_stalls, gen_stalls, \
                            (squashing + rob_empty).rename('Frontend Stalls')]

                else:
                    empty_series = pd.Series({'mean': 0})
                    #cycles       = df['sim_ticks'] / 500
                    cycles       = empty_series
                    #commit       = df['system.cpu.committedInsts'].rename('commit')
                    commit       = empty_series.rename('Commit')
                    gen_stalls   = (cycles - commit).rename('Backend Stalls')
                    mem_stalls   = empty_series.rename('Memory Stalls')
                    squashing    = empty_series.rename('squashing')
                    rob_empty    = empty_series.rename('rob_empty')
                    components   = [commit, mem_stalls, gen_stalls,
                        (squashing + rob_empty).rename('Frontend Stalls')]
                    #components   = [commit, mem_stalls, gen_stalls, other]


                combined_df = pd.DataFrame(components)
                all_reasons = combined_df['mean']
                sum_all_reasons = combined_df['mean'].sum()

                all_reasons /= sum_all_reasons
                all_reasons *= cpi_ratio

                stat_per_config[config_name] = all_reasons


            benchmark_df = pd.DataFrame(stat_per_config)
            benchmark_dfs[benchmark] = benchmark_df.T

        return pd.concat(dict(benchmark_dfs), axis=0)

    def calculate_cpi_breakdown_avg(self, dfs):
        prefix_fn = lambda s: 'system.cpu.commit.commitCyclesBreakDown::{}'.format(s)
        benchmark_dfs = {}
        for benchmark, config_data in dfs.items():
            baseline_cpi = config_data['o3']['cpi']['mean']

            stat_per_config = defaultdict(dict)
            for config_name, df in config_data.items():

                config_cpi = df['cpi']['mean']
                cpi_ratio  = config_cpi / baseline_cpi

                df = df.fillna(0.0)

                components = []
                if 'inorder' not in config_name and \
                    'invisiblespec' not in config_name and \
                    'invisispec' not in config_name:
                    gen_stalls = (df[prefix_fn('GeneralStall')]     + \
                                  df[prefix_fn('InstructionFault')]).rename('Backend Stalls')
                    mem_stalls = (df[prefix_fn('LoadStall')]    + \
                                  df[prefix_fn('StoreStall')]   + \
                                  df[prefix_fn('LoadOrder')]    + \
                                  df[prefix_fn('StoreOrder')]   + \
                                  df[prefix_fn('MemBarrier')]   + \
                                  df[prefix_fn('WriteBarrier')]).rename('Memory Stalls')
                    squashing  = (df[prefix_fn('SquashingBranchMispredict')] + \
                                  df[prefix_fn('SquashingMemoryViolation')]  + \
                                  df[prefix_fn('RetiringSquashes')]).rename('squashing')
                    commit     = df[prefix_fn('CommitSuccess')].rename('Commit')
                    rob_empty  = df[prefix_fn('ROBEmpty')].rename('rob_empty')
                    total      = df[prefix_fn('total')]
                    other      = (total - (gen_stalls + mem_stalls + \
                                squashing + commit + rob_empty)).rename('other')
                    assert other['mean']/total['mean'] <= 0.01
                    components = [commit, mem_stalls, gen_stalls, \
                            (squashing + rob_empty).rename('Frontend Stalls')]

                else:
                    empty_series = pd.Series({'mean': 0})
                    #cycles       = df['sim_ticks'] / 500
                    cycles       = empty_series
                    #commit       = df['system.cpu.committedInsts'].rename('commit')
                    commit       = empty_series.rename('Commit')
                    gen_stalls   = (cycles - commit).rename('Backend Stalls')
                    mem_stalls   = empty_series.rename('Memory Stalls')
                    squashing    = empty_series.rename('squashing')
                    rob_empty    = empty_series.rename('rob_empty')
                    components   = [commit, mem_stalls, gen_stalls,
                        (squashing + rob_empty).rename('Frontend Stalls')]
                    #components   = [commit, mem_stalls, gen_stalls, other]


                combined_df = pd.DataFrame(components)
                all_reasons = combined_df['mean']

                stat_per_config[config_name] = all_reasons

            benchmark_df = pd.DataFrame(stat_per_config)
            benchmark_dfs[benchmark] = benchmark_df.T

        df = pd.concat(dict(benchmark_dfs), axis=0)
        df = df.mean(level=1)

        cpi_df = self.average_stats(self.filter_stats('cpi',
                    self.reorder_data_frames(dfs)))

        norm = cpi_df['o3']['mean']

        for config in df.index:
            cpi = cpi_df[config]['mean']
            cpi_ratio = cpi / norm

            # normalize the components
            df.T[config] /= df.T[config].sum()

            # then scale by CPI
            df.T[config] *= cpi_ratio

        return df
