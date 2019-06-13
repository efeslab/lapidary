from __future__ import print_function
from argparse import ArgumentParser
from collections import defaultdict
from IPython import embed
import itertools
import json
import enum
from enum import Enum
from math import sqrt, ceil
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
from matplotlib.patches import Patch
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import matplotlib.ticker as ticker
from pathlib import Path
from pprint import pprint
import re
import numpy as np

import Utils
from SpecBench import *

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)
#pd.set_option('display.max_rows', None)

class Grapher:

    COLORS  = ['b', 'c', 'g', 'y', 'r', 'm', 'k']
    SHAPES  = ['o', 'v', '8', 's', 'P', '*', 'X']

    D       = 5
    HATCH   = [D*'..', D*'\\\\', D*'//', D*'', D*'xx', D*'*', D*'+', D*'\\']

    CONFIG_NAMES = {
            'cooldown_eagerloadsprotection':          'Restricted Loads',
            'cooldown_maximumprotection':             'Full Protection',
            'cooldown_branchprotection_liberal':      'Permissive',
            'cooldown_branchprotection_conservative': 'Strict',
            'inorder':                                'In-Order',
            'o3':                                     'OoO',
            'cooldown_empty':                         'OoO',
    }

    CONFIG_COLOR = {
            'Restricted Loads': '#91bfdb',
            'Full Protection':  '#fc8d59',
            'Permissive':       '#fee090',
            'Strict':           '#4575b4',
            'In-Order':         '#d73027',
            'OoO':              '#e0f3f8',
    }

    CONFIG_ORDER = {
            'OoO':              0,
            'Permissive':       1,
            'Strict':           2,
            'Restricted Loads': 3,
            'Full Protection':  4,
            'In-Order':         5,
    }

    @staticmethod
    def _hex_color_to_tuple(color_str):
        r = int(color_str[1:3], 16) / 256.0
        g = int(color_str[3:5], 16) / 256.0
        b = int(color_str[5:7], 16) / 256.0
        return (r, g, b)


    def __init__(self, args):
        self.input_file = Path(args.input_file)
        self.output_dir = Path(args.output_dir)
        assert self.input_file.exists()
        assert self.output_dir.exists()
        with self.input_file.open() as f:
            self.report      = json.load(f)
            self.results     = self.report['results']
            self.checkpoints = self.report['checkpoints']

        plt.rcParams['hatch.linewidth'] = 0.5
        plt.rcParams['font.family']     = 'serif'
        plt.rcParams['font.size']       = 6
        plt.rcParams['axes.labelsize']  = 6

        self.barchart_defaults = {
                                    'edgecolor': 'black',
                                    'linewidth': 1.0,
                                 }

        self._reconstitute_data_frames()

    def _reconstitute_data_frames(self):
        self.data_frames = defaultdict(dict)
        for benchmark, config_data in self.results.items():
            for config_name, raw_df in config_data.items():
                df = pd.DataFrame(raw_df)
                self.data_frames[benchmark][config_name] = df

    def _reorder_data_frames(self):
        new_frames = defaultdict(dict)
        for benchmark, config_data in self.data_frames.items():
            for config_name, config_df in config_data.items():
                new_frames[config_name][benchmark] = config_df

        return new_frames

    @staticmethod
    def _clean_benchmark_names(benchmark_names):
        new_names = []
        for b in benchmark_names:
            try:
                bench = b.split('.')[1].split('_')[0]
                new_names += [bench]
            except:
                raise Exception('Could not parse benchmark {}'.format(b))
        return new_names

    @staticmethod
    def _do_grid_lines():
        plt.grid(color='0.5', linestyle='--', axis='y', dashes=(2.5, 2.5))
        plt.grid(which='major', color='0.7', linestyle='-', axis='x', zorder=5.0)

    @classmethod
    def _reorder_configs(cls, df):
        columns = df.columns.unique(0).tolist()
        order = lambda s: cls.CONFIG_ORDER[s]
        sorted_columns = sorted(columns, key=order)
        return df[sorted_columns]

    @classmethod
    def _get_values_per_config(cls, dataframes, stat_name):
        index     = 0
        positions = []
        labels    = []
        means_per_config = {}
        error_per_config = {}
        perct_per_config = {}

        skip_inorder = False

        for config_name, benchmark_data in dataframes.items():
            stat_per_benchmark = {}

            for benchmark, df in benchmark_data.items():
                if stat_name not in df:
                    if 'inorder' in config_name:
                        skip_inorder = True
                        continue
                    else:
                        raise Exception('Config {} does not have {}'.format(
                            config_name, stat_name))

                stat_per_benchmark[benchmark] = df[stat_name]

            if skip_inorder and 'inorder' in config_name:
                continue

            config_df = pd.DataFrame(stat_per_benchmark).T
            config_means = config_df['mean']
            config_error = config_df['ci']
            config_perct = (config_error * 100.0) / config_means

            label_name = config_name
            if config_name in cls.CONFIG_NAMES:
                label_name = cls.CONFIG_NAMES[config_name]

            means_per_config[label_name] = config_means
            error_per_config[label_name] = config_error
            perct_per_config[label_name] = config_perct

            new_pos = range(len(list(config_df.T.columns)))
            new_lab = list(config_df.T.columns)

            if len(positions) == 0:
                positions = new_pos
                labels    = new_lab
            else:
                assert positions == new_pos
                assert labels    == new_lab

            index += 1

        all_means = cls._reorder_configs(pd.DataFrame(means_per_config))
        all_error = cls._reorder_configs(pd.DataFrame(error_per_config))
        all_perct = cls._reorder_configs(pd.DataFrame(perct_per_config))

        return all_means, all_error, all_perct, labels

    def graph_cache_misses(self, bench_filter):
        dataframes = self.data_frames

        assert bench_filter is None or isinstance(bench_filter, list)

        index     = 0
        positions = []
        labels    = []

        for benchmark, config_data in dataframes.items():
            if bench_filter is not None and benchmark not in bench_filter:
                continue

            misses_all = defaultdict(dict)
            for config, df in config_data.items():
                cycles = df['sim_ticks'] / 500.0
                embed()
                misses_all['icache_reg'][config] = 40.0  * df['system.cpu.icache.cacheMisses::Regular'] / cycles
                misses_all['icache_run'][config] = 40.0  * df['system.cpu.icache.cacheMisses::Runahead'] / cycles

                misses_all['dcache_reg'][config] = 40.0  * df['system.cpu.dcache.cacheMisses::Regular'] / cycles
                misses_all['dcache_run'][config] = 40.0  * df['system.cpu.dcache.cacheMisses::Runahead'] / cycles

                misses_all['l2_reg'][config]     = 300.0 * df['system.l2.cacheMisses::Regular'] / cycles
                misses_all['l2_run'][config]     = 300.0 * df['system.l2.cacheMisses::Runahead'] / cycles

            index = 0
            reg_means  = []
            run_means  = []
            for reg, run in [ ('icache_reg', 'icache_run'),
                              ('dcache_reg', 'dcache_run'),
                              ('l2_reg',     'l2_run'    )]:

                reg_miss_df = pd.DataFrame(misses_all[reg])
                run_miss_df = pd.DataFrame(misses_all[run])

                reg_means  += [reg_miss_df.mean().rename(reg)]
                run_means  += [run_miss_df.mean().rename(run)]

                new_pos = range(len(list(reg_miss_df.columns)))
                new_lab = list(reg_miss_df.columns)

                if len(positions) == 0:
                    positions = new_pos
                    labels    = new_lab
                else:
                    assert positions == new_pos
                    assert labels    == new_lab

            all_reg = pd.DataFrame(reg_means).T
            #all_run = pd.DataFrame(run_means).T
            #all_reg = pd.DataFrame(sum(reg_means))

            all_reg.plot.bar()
            #all_run.plot.bar(bottom=all_reg)


        #labels = [ l.replace('cooldown', 'CD') for l in labels ]

        legend = plt.legend(loc=2)
        plt.ylabel('Cache Miss Latency Per Cycle')
        #plt.xticks(positions, labels)#, rotation='-40', ha='left')
        plt.xlabel('CPU Configuration')
        plt.title('SPEC2017 Performance Comparison')
        plt.grid(color='y', linestyle='--', axis='y', dashes=(2, 10))
        plt.grid(color='y', linestyle='--', axis='x')

        plt.savefig(self.output_file, bbox_inches='tight')
        plt.close()


    def _add_stat_to_subplot(self, dataframes, grid_spec, stat, cutoff, xlabel, no_label=False, error_bars=True):
        all_means, all_error, all_perct, labels = self._get_values_per_config(
                dataframes, stat)

        if error_bars:
            threshold = 0.05
            print('{} graph: Setting error bar minimum to +/- {} for visibility'.format(
                stat, threshold))
            print(all_error)
            all_error = all_error.clip(lower=threshold)
            print(all_error)

        num_configs = len(all_means.columns)
        width = num_configs / (num_configs + 1)

        max_val = (all_means + all_error + 0.5).max().max()
        axis = plt.subplot(grid_spec)
        axis.set_xlim(0.0, cutoff)
        axis.margins(x=0, y=0)
        ax = all_means.plot.barh(ax=axis,
                                 xerr=all_error if error_bars else None,
                                 width=width,
                                 color='0.75',
                                 **self.barchart_defaults)

        text_df = all_means.T
        for i, bench in enumerate(text_df):
            for j, v in enumerate(reversed(text_df[bench])):
                y = i - ((j - 3.0) / (len(text_df) + 1))
                s = '{0:.1f}'.format(v) if v >= cutoff else ''
                txt = ax.text(cutoff * 0.9, y, s, color='white',
                              fontweight='bold', fontfamily='sans',
                              fontsize=6)
                txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])

        ybounds = axis.get_ylim()

        artist = []
        labels = self._clean_benchmark_names(labels)

        ax.invert_yaxis()
        major_tick = max(float(int(cutoff / 10.0)), 1.0)
        if major_tick > 10.0:
            major_tick = 5.0 * int(major_tick / 5)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(major_tick))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(major_tick / 5.0))
        ax.set_axisbelow(True)

        bars = ax.patches

        num_configs = all_means.shape[1]
        num_bench   = all_means.shape[0]
        hatches = (self.__class__.HATCH * 10)[:num_configs]
        all_hatches = sum([ list(itertools.repeat(h, num_bench))
            for h in hatches ], [])

        colors = [self.__class__.CONFIG_COLOR[c] for c in all_means.columns ]
        all_colors = sum([ list(itertools.repeat(c, num_bench))
            for c in colors ], [])

        for bar, hatch, color in zip(bars, all_hatches, all_colors):
            #bar.set_hatch(hatch)
            bar.set_color(color)
            bar.set_edgecolor('black')

        plt.sca(axis)
        self.__class__._do_grid_lines()

        plt.xlabel(xlabel)

        if no_label:
            plt.yticks(ticks=range(len(labels)), labels=['']*len(labels))
            axis.legend().set_visible(False)
            return None
        else:
            plt.yticks(ticks=range(len(labels)), labels=labels, rotation='45', ha='right')
            legend = plt.legend(loc='best', prop={'size': 6})
            artist += [legend]

            return artist, ybounds

    def _add_commit_cycle_breakdown_to_subplot(self, dataframes, grid_spec, ybounds, cutoff):
        benchmark_dfs = {}
        once = False
        for benchmark, config_data in dataframes.items():
            baseline_cpi = dataframes[benchmark]['o3']['cpi']['mean']

            stat_per_config = defaultdict(dict)
            for config_name, df in config_data.items():

                config_cpi = df['cpi']['mean']
                cpi_ratio  = config_cpi / baseline_cpi

                components = []
                if 'inorder' not in config_name:
                    gen_stalls = (df['system.cpu.commit.commitCyclesBreakDown::GeneralStall']     + \
                                  df['system.cpu.commit.commitCyclesBreakDown::InstructionFault']).rename('Backend Stalls')
                    mem_stalls = (df['system.cpu.commit.commitCyclesBreakDown::LoadStall']    + \
                                  df['system.cpu.commit.commitCyclesBreakDown::StoreStall']   + \
                                  df['system.cpu.commit.commitCyclesBreakDown::LoadOrder']    + \
                                  df['system.cpu.commit.commitCyclesBreakDown::StoreOrder']   + \
                                  df['system.cpu.commit.commitCyclesBreakDown::MemBarrier']   + \
                                  df['system.cpu.commit.commitCyclesBreakDown::WriteBarrier']).rename('Memory Stalls')
                    squashing  = (df['system.cpu.commit.commitCyclesBreakDown::SquashingBranchMispredict'] + \
                                  df['system.cpu.commit.commitCyclesBreakDown::SquashingMemoryViolation']  + \
                                  df['system.cpu.commit.commitCyclesBreakDown::RetiringSquashes']).rename('squashing')
                    commit     = df['system.cpu.commit.commitCyclesBreakDown::CommitSuccess'].rename('Commit')
                    rob_empty  = df['system.cpu.commit.commitCyclesBreakDown::ROBEmpty'].rename('rob_empty')
                    total      = df['system.cpu.commit.commitCyclesBreakDown::total']
                    other      = (total - (gen_stalls + mem_stalls + squashing + commit + rob_empty)).rename('other')
                    assert other['mean'] < 1.0
                    components = [commit, mem_stalls, gen_stalls, (squashing + rob_empty).rename('Frontend Stalls')]
                    '''
                    gen_stalls = df['system.cpu.commit.commitCyclesBreakDown::GeneralStall'].rename('General stalls')
                    mem_stalls = (df['system.cpu.commit.commitCyclesBreakDown::LoadStall']    + \
                                  df['system.cpu.commit.commitCyclesBreakDown::StoreStall']).rename('memory stalls')
                    commit     = df['system.cpu.commit.commitCyclesBreakDown::CommitSuccess'].rename('commit')
                    total      = df['system.cpu.commit.commitCyclesBreakDown::total']
                    other      = (total - (gen_stalls + mem_stalls + commit)).rename('other')
                    components = [commit, mem_stalls, gen_stalls, other]
                    '''

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

                label_name = config_name
                if config_name in self.__class__.CONFIG_NAMES:
                    label_name = self.__class__.CONFIG_NAMES[config_name]

                stat_per_config[label_name] = all_reasons

            benchmark_df = pd.DataFrame(stat_per_config)
            benchmark_dfs[benchmark] = benchmark_df.T

        all_dfs   = pd.concat(dict(benchmark_dfs), axis=0)
        df_list   = [ df for name, df in benchmark_dfs.items()   ]
        df_labels = [ name for name, df in benchmark_dfs.items() ]

        axis = plt.subplot(grid_spec)

        # reversed for top to bottom
        index = np.arange(len(benchmark_dfs))[::-1]
        dfs = all_dfs.swaplevel(0,1).sort_index().T
        max_val = ceil(dfs.sum().max() + 0.6)
        axis.set_xlim(0, cutoff)
        axis.margins(x=0, y=0)

        dfs = self.__class__._reorder_configs(dfs)

        n = 0.0
        num_slots = float(len(dfs.columns.unique(0)) + 1)
        width = 1.0 / num_slots

        config_index = 0
        hatches = self.__class__.HATCH
        labels = None

        config_patches = []
        reason_patches = []
        for config in dfs.columns.unique(0):
            bottom = None
            df = dfs[config].T

            config_color = self.__class__.CONFIG_COLOR[config]
            config_color = np.array(self.__class__._hex_color_to_tuple(config_color))
            reason_index = 0

            for reason in df.columns:
                data = df[reason].values

                hatch = hatches[reason_index % len(hatches)]

                #new_index = index + ((n + 1.0 - (num_slots / 2.0)) * width)
                new_index = index - ((n + 1.0 - (num_slots / 2.0)) * width)
                #new_index = index - (1.0 - ((n + 1.0 - (num_slots / 2.0)) * width))

                axis.barh(new_index,
                          data,
                          height=width,
                          left=bottom,
                          color=config_color,
                          hatch=hatch,
                          label=config,
                          **self.barchart_defaults)


                bottom = data if bottom is None else data + bottom
                reason_index += 1

                for i, d, name in zip(new_index, bottom, df[reason].index):
                    s = '{0:.1f}'.format(d) if d >= cutoff else ''
                    txt = axis.text(cutoff * 0.9, i - (0.5 * width), s, color='white',
                                    fontweight='bold', fontfamily='sans',
                                    fontsize=6)
                    txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])

                if labels is None:
                    labels = df[reason].index

            config_patches += [Patch(facecolor=config_color, edgecolor='black',
                                     label=config)]

            if len(reason_patches) == 0:
                for reason, hatch, i in zip(df.columns, hatches, itertools.count()):
                    reason_patches += [Patch(facecolor='white',
                                             edgecolor='black',
                                             hatch=hatch,
                                             label=reason)]

            n += 1.0
            config_index += 1

        plt.sca(axis)
        num_bench = len(dataframes)
        plt.yticks(ticks=np.arange(num_bench), labels=['']*num_bench)
        axis.set_ylim(*ybounds)
        #config_legend = plt.legend(handles=config_patches, loc='center right')
        reason_legend = plt.legend(handles=reason_patches, loc='best',
                                    prop={'size': 6})
        #axis.add_artist(config_legend)

        interval = 1.0
        #axis.tick_params(labelsize=4)
        axis.xaxis.set_major_locator(ticker.MultipleLocator(interval))
        axis.xaxis.set_minor_locator(ticker.MultipleLocator(interval / 5.0))
        axis.set_axisbelow(True)

        plt.xlabel('Cycles break-down, normalized to O3')

        self.__class__._do_grid_lines()

        #return [config_legend, reason_legend]
        return [reason_legend]


    def graph_cpi_with_breakdown(self):
        dataframes = self._reorder_data_frames()

        cpi_gs, brk_gs = GridSpec(1, 2)

        artist, ybounds = self._add_stat_to_subplot(dataframes, cpi_gs, 'cpi',
                7.8, 'Cycles per Instruction')
        artist += self._add_commit_cycle_breakdown_to_subplot(
                        self.data_frames, brk_gs, ybounds, 3.6)

        plt.subplots_adjust(wspace=0.05, hspace=0.0)

        fig = plt.gcf()
        fig.set_size_inches(7.0, 8.5)
        fig.tight_layout()

        #output_file = str(self.output_dir / 'cpi_breakdown_graph.pdf')
        output_file = str(self.output_dir / 'cpi_breakdown_graph.png')
        plt.savefig(output_file, dpi=300,
                    bbox_inches='tight', pad_inches=0.02,
                    additional_artists=artist)
        plt.close()

    def graph_mlp_with_latency(self):
        dataframes = self._reorder_data_frames()

        mlp_gs, lat_gs = GridSpec(1, 2)

        artist, _ = self._add_stat_to_subplot(dataframes, mlp_gs, 'MLP', 18.0,
                'Memory-Level Parallelism', error_bars=False)
        self._add_stat_to_subplot(dataframes, lat_gs, 'avgLatencyToIssue',
                120.0, 'Cycles', no_label=True, error_bars=False)

        plt.subplots_adjust(wspace=0.05, hspace=0.0)

        fig = plt.gcf()
        fig.set_size_inches(7.0, 8.5)
        fig.tight_layout()

        output_file = str(self.output_dir / 'mlp_with_latency_graph.pdf')
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0.02,
                additional_artists=artist)
        plt.close()


    def graph_single_stat(self, stat):
        dataframes = self._reorder_data_frames()

        axis = plt.subplot(1, 1, 1)

        artist = self._add_stat_to_subplot(dataframes, axis, stat)

        fig = plt.gcf()
        fig.set_size_inches(3.5, 8.5)

        output_file = str(self.output_dir / '{}_graph.pdf'.format(stat))
        plt.savefig(output_file, bbox_inches='tight',
                additional_artists=artist)
        plt.close()


    def graph_checkpoints(self, benchmark):
        '''
          Show how spred out the checkpoints are that run successfully.
        '''
        import matplotlib.pyplot as plt
        import pandas as pd

        dataframe = pd.DataFrame(self.checkpoints[benchmark]).T
        datamean = dataframe.mean()
        datamean.plot.bar(color='g', width=1.0)

        datainv = 1.0 - datamean
        ax = datainv.plot.bar(bottom=datamean, color='r', width=1.0)

        ticks = ax.xaxis.get_ticklocs()
        ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]

        n = int(len(ticks) / 10)

        ax.xaxis.set_ticks(ticks[::n])
        ax.xaxis.set_ticklabels(ticklabels[::n])

        plt.xlabel('Checkpoint Number')
        plt.ylabel('Average Validity across Configurations')
        plt.title('Checkpoint Validity Distribution for {}'.format(benchmark))
        plt.savefig(self.output_file, bbox_inches='tight')
        plt.close()

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
        dataframes = self.data_frames

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

        perm   = 'cooldown_branchprotection_liberal'
        strict = 'cooldown_branchprotection_conservative'
        nda    = 'cooldown_eagerloadsprotection'
        maxp = 'cooldown_maximumprotection'
        o3   = 'o3'
        inor = 'inorder'

        print('='*80)
        for bench, data in cpi_mean.iteritems():
            if data[o3] > data.min():
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
        configs = [[perm, 'Perm'], [strict, 'Strict'], [nda, 'NDA-Loads'], [maxp, 'Max-Prot'], [inor, 'I-O']]
        for c, name in configs:
            print('\nCPI Percent Slowdown ({})'.format(name))
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

            gap = ((cpi_mean.T[inor] - cpi_mean.T[c]) / (cpi_mean.T[inor] - cpi_mean.T[o3]))
            print('CPI Percent Gap Closed ({})'.format(name))
            p_percent('Min', gap.min())
            p_percent('Max', gap.max())
            p_percent('Mean', gap.mean())

            print('Number of checkpoints ({})'.format(name))
            print('--- Min: {0:.0f}'.format(cpi_count.T[c].min()))
            print('--- Max: {0:.0f}'.format(cpi_count.T[c].max()))
            print('--- Mean: {0:.0f}'.format(cpi_count.T[c].mean()))

