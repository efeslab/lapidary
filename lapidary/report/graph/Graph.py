from __future__ import print_function

from IPython import embed
from argparse import ArgumentParser
from collections import defaultdict
from enum import Enum
from math import sqrt, ceil, isnan
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.patches import Patch
from pathlib import Path
from pprint import pprint
import copy
import enum
import itertools
import json
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import re
import yaml

import lapidary.utils as Utils
from lapidary.config.specbench import *

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)
#pd.set_option('display.max_rows', None)

class Grapher:

    D       = 5
    HATCH   = [D*'..', D*'\\\\', D*'//', D*'', D*'xx', D*'*', D*'+', D*'\\']

    def _hex_color_to_tuple(self, color_str):
        r = int(color_str[1:3], 16) / 256.0
        g = int(color_str[3:5], 16) / 256.0
        b = int(color_str[5:7], 16) / 256.0
        return (r, g, b)

    def __init__(self, args):
        self.config_file = Path(args.config)
        assert self.config_file.exists()

        with self.config_file.open() as f:
            self.config = yaml.safe_load(f)

        plt.rcParams['hatch.linewidth'] = 0.5
        plt.rcParams['font.family']     = 'serif'
        plt.rcParams['font.size']       = 6
        plt.rcParams['axes.labelsize']  = 6

        self.barchart_defaults = {
                                    'edgecolor': 'black',
                                    'linewidth': 0.7,
                                    'error_kw': {
                                        'elinewidth': 1.0,
                                        }
                                 }

    def _get_config_name(self, config_name):
        name = config_name.lower()
        if name in self.config['display_options']['config_names']:
            return self.config['display_options']['config_names'][name]
        return config_name

    def _get_config_color(self, config_name):
        name = self._get_config_name(config_name)
        color = '#000000'
        if name in self.config['display_options']['config_colors']:
            color = self.config['display_options']['config_colors'][name]
        return self._hex_color_to_tuple(color)

    def _get_config_order(self, config_name):
        name = self._get_config_name(config_name)
        order_list = self.config['display_options']['config_order']
        order = len(order_list)
        if name in order_list:
            order = order_list.index(name)
        return order

    @staticmethod
    def _clean_benchmark_names(benchmark_names):
        new_names = []
        for b in benchmark_names:
            try:
                bench = b.split('.')[1].split('_')[0]
                new_names += [bench]
            except:
                new_names += [b]
        return new_names

    @staticmethod
    def _do_grid_lines():
        plt.grid(color='0.5', linestyle='--', axis='y', dashes=(2.5, 2.5))
        plt.grid(which='major', color='0.7', linestyle='-', axis='x', zorder=5.0)

    def _rename_configs(self, df):
        columns = df.columns.unique(0).tolist()
        new_columns = {c: self._get_config_name(c) for c in columns}
        return df.rename(columns=new_columns)

    def _rename_multi_index(self, df):
        df = df.sort_index(level=1)
        index = df.index.unique(1).tolist()
        new_index = [self._get_config_name(c) for c in index]
        df.index = df.index.set_levels(new_index, level=1)
        return df

    def _reorder_configs(self, df):
        columns = df.columns.unique(0).tolist()
        order_fn = lambda s: self._get_config_order(s)
        sorted_columns = sorted(columns, key=order_fn)
        return df[sorted_columns]

        return all_means, all_error, all_perct, labels

    def _kwargs_bool(self, kwargs_dict, field):
        if field not in kwargs_dict or not kwargs_dict[field]:
            return False
        return True

    def _kwargs_default(self, kwargs_dict, field, default_val):
        if field not in kwargs_dict:
            return default_val
        return kwargs_dict[field]

    def _kwargs_has(self, kwargs_dict, field):
        return field in kwargs_dict and kwargs_dict[field] is not None

    def graph_single_stat(self, means_df, ci_df, axis, **kwargs):
        all_means = self._rename_configs(self._reorder_configs(means_df))
        all_error = self._rename_configs(self._reorder_configs(ci_df))
        all_perct = None
        labels = means_df.index

        if self._kwargs_bool(kwargs, 'error_bars'):
            threshold = 0.05
            print('Setting error bar minimum to +/- {} for visibility'.format(threshold))
            #print(all_error)
            all_error = all_error.clip(lower=threshold)
            if 'Average' in all_error.index:
                all_error.loc['Average'][:] = 0.0
            #print(all_error)
        else:
            all_error[:] = 0

        num_configs = len(all_means.columns)
        width = num_configs / (num_configs + 2)
        bar_width = width / num_configs

        max_val = (all_means + all_error + 0.5).max().max()
        cutoff = self._kwargs_default(kwargs, 'cutoff', max_val)
        axis.set_xlim(0.0, cutoff)
        axis.margins(0.0)

        ax = all_means.plot.barh(ax=axis,
                                 xerr=all_error,
                                 width=width,
                                 color='0.75',
                                 **self.barchart_defaults)

        text_df = all_means.T
        min_y_pos = 0.0
        max_y_pos = 0.0
        for i, bench in enumerate(text_df):
            for j, v in enumerate(reversed(text_df[bench])):
                offset = (j * bar_width) - (bar_width * (num_configs / 2)) + \
                        (bar_width / 2)
                y = i - offset
                min_y_pos = min(y - (bar_width / 2), min_y_pos)
                max_y_pos = max(y + (bar_width / 2), max_y_pos)
                precision = self._kwargs_default(kwargs, 'precision', 1)
                s = (' {0:.%df} ' % precision).format(v) if v >= cutoff or \
                        self._kwargs_bool(kwargs, 'add_numbers') else ''
                pos = cutoff if v >= cutoff else v
                if isnan(pos):
                    continue
                txt = ax.text(pos, y, s, va='center',
                              ha=self._kwargs_default(kwargs, 'number_align', 'right'),
                              color='white',
                              fontweight='bold', fontfamily='sans',
                              fontsize=6)
                txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])

                if self._kwargs_bool(kwargs, 'label_bars'):
                    label_txt = ' ' + list(reversed(text_df[bench].index.tolist()))[j]
                    txt2 = ax.text(0, y, label_txt, va='center', ha='left',
                                   color='white', fontweight='bold', fontfamily='sans',
                                   fontsize=6)
                    txt2.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])

        ybounds = axis.get_ylim()
        if self._kwargs_bool(kwargs, 'flush'):
            axis.set_ylim(min_y_pos, max_y_pos)

        artist = []
        labels = self._clean_benchmark_names(labels)

        ax.invert_yaxis()
        major_tick = max(float(int(cutoff / 10.0)), 1.0)
        if major_tick > 10.0:
            major_tick = 5.0 * int(major_tick / 5)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(major_tick))
        if cutoff > 5.0:
            ax.xaxis.set_minor_locator(ticker.MultipleLocator(major_tick / 5.0))
        else:
            ax.xaxis.set_minor_locator(ticker.MultipleLocator(major_tick / 10.0))
        ax.set_axisbelow(True)

        bars = ax.patches

        num_configs = all_means.shape[1]
        num_bench   = all_means.shape[0]
        hatches = (self.__class__.HATCH * 10)[:num_configs]
        all_hatches = sum([ list(itertools.repeat(h, num_bench))
            for h in hatches ], [])

        colors = [self._get_config_color(c) for c in all_means.columns ]
        all_colors = sum([ list(itertools.repeat(c, num_bench))
            for c in colors ], [])

        for bar, hatch, color in zip(bars, all_hatches, all_colors):
            #bar.set_hatch(hatch)
            bar.set_color(color)
            bar.set_edgecolor('black')

        scale = self._kwargs_default(kwargs, 'scale', 1.0)
        if scale < 1.0:
            print('Scaling!')
            box = axis.get_position()
            new_box = [box.x0, box.y0 + box.height * (1.0 - scale),
                       box.width, box.height * scale]
            axis.set_position(new_box)

        plt.sca(axis)
        self.__class__._do_grid_lines()

        plt.xlabel(self._kwargs_default(kwargs, 'label', ''), labelpad=0)

        if self._kwargs_bool(kwargs, 'exclude_tick_labels'):
            plt.yticks(ticks=range(len(labels)), labels=['']*len(labels))
        else:
            plt.yticks(ticks=range(len(labels)), labels=labels, rotation='45', ha='right')

            minor_ticks = []
            if self._kwargs_has(kwargs, 'per_tick_label'):
                # Required to determine position of ticks.
                plt.gcf().canvas.draw()
                for tick in axis.yaxis.get_major_ticks():
                    tick_label = tick.label.get_text()
                    if tick_label not in kwargs['per_tick_label']:
                        continue

                    opt = kwargs['per_tick_label'][tick_label]

                    if 'font' in opt:        
                        from matplotlib.font_manager import FontProperties  
                        tick.label.set_fontproperties(FontProperties(**opt['font']))

                    if self._kwargs_bool(opt, 'line_before'):
                        minor_ticks += [tick.get_loc() - 0.5]

            if len(minor_ticks):
                axis.yaxis.set_minor_locator(ticker.FixedLocator(minor_ticks))
                axis.tick_params(which='minor', axis='y', length=0, width=0)
                plt.grid(which='minor', color='k', linestyle='-', axis='y',
                        zorder=5.0, linewidth=2)


        if self._kwargs_has(kwargs, 'legend'):
            legend = plt.legend(**kwargs['legend'])
            artist += [legend]
        else:
            plt.legend().set_visible(False)

        return artist, ybounds

    def graph_grouped_stacked_bars(self, dataframes, axis, **kwargs):
        dataframes = self._rename_multi_index(dataframes)

        df_list   = [ df for name, df in dataframes.items()   ]
        df_labels = [ name for name, df in dataframes.items() ]

        num_bench = dataframes.index.levshape[0]
        # reversed for top to bottom
        index = np.arange(num_bench)[::-1]
        dfs = dataframes.swaplevel(0,1).sort_index().T
        max_val = ceil(dfs.sum().max() + 0.6)
        cutoff = self._kwargs_default(kwargs, 'cutoff', max_val)
        axis.set_xlim(0, cutoff)
        axis.margins(x=0, y=0)

        dfs = self._reorder_configs(dfs)

        n = 0.0
        num_slots = float(len(dfs.columns.unique(0)) + 1)
        width = 1.0 / num_slots
        print(num_slots, width)

        config_index = 0
        hatches = self.__class__.HATCH
        labels = None

        config_patches = []
        reason_patches = []
        for config in dfs.columns.unique(0):
            bottom = None
            df = dfs[config].T

            config_color = np.array(self._get_config_color(config))
            reason_index = 0

            new_index = index - ((n + 1.0 - (num_slots / 2.0)) * width)

            for reason in df.columns:
                data = df[reason].values

                hatch = hatches[reason_index % len(hatches)]


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
                #offset = (i * width) - (width * (num_slots / 2)) - (width / 2)
                #y = i - offset
                y = i
                precision = self._kwargs_default(kwargs, 'precision', 1)
                s = (' {0:.%df} ' % precision).format(d)
                pos = cutoff if cutoff < d else d
                if isnan(pos):
                    continue
                print(pos, y)
                txt = axis.text(pos, y, s, va='center', color='white',
                                ha=self._kwargs_default(kwargs, 'number_align', 'right'),
                                fontweight='bold', fontfamily='sans',
                                fontsize=6)
                txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])

                if self._kwargs_bool(kwargs, 'label_bars'):
                    txt2 = axis.text(0, y, ' ' + config, va='center', ha='left', color='white',
                                    fontweight='bold', fontfamily='sans',
                                    fontsize=6)
                    txt2.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='black')])


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
        plt.yticks(ticks=np.arange(num_bench), labels=['']*num_bench)
        #axis.set_ylim(*ybounds)

        config_legend = None
        reason_legend = None
        if self._kwargs_bool(kwargs, 'config_legend'):
            config_legend = plt.legend(handles=config_patches, **kwargs['legend'])
        if self._kwargs_bool(kwargs, 'breakdown_legend'):
            reason_legend = plt.legend(handles=reason_patches, **kwargs['legend'])
            if self._kwargs_bool(kwargs, 'config_legend'):
                axis.add_artist(config_legend)

        interval = 1.0
        #axis.tick_params(labelsize=4)
        axis.xaxis.set_major_locator(ticker.MultipleLocator(interval))
        axis.xaxis.set_minor_locator(ticker.MultipleLocator(interval / 10.0))
        axis.set_axisbelow(True)

        plt.xlabel(self._kwargs_default(kwargs, 'label', ''))

        self.__class__._do_grid_lines()

        return [x for x in [config_legend, reason_legend] if x is not None]


    def _get_stat_attribute(self, dataframes, stat, attr):
        stat_data = {}
        for bench, config_dict in dataframes.items():
            stats = {}
            for config, df in config_dict.items():
                stats[config] = df[stat][attr]
            per_bench = pd.Series(stats)
            stat_data[bench] = per_bench

        return pd.DataFrame(stat_data)

    def output_text(self, dataframes):
        cpi_mean  = self._get_stat_attribute(dataframes, 'cpi', 'mean')
        cpi_ci    = self._get_stat_attribute(dataframes, 'cpi', 'ci')
        cpi_count = self._get_stat_attribute(dataframes, 'cpi', 'count')
        cpi_ci_p  = cpi_ci / cpi_mean

        #for bench, data in cpi_count.iteritems():
        #    assert data.min() == data.max()

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

    def output_means(self, cpi_mean):
        o3   = 'o3'
        inor = 'inorder'
        p_percent = lambda l, x: print('--- {0}: {1:.1f}%'.format(l, x * 100.0))
        p_times = lambda l, x: print('--- {0}: {1:.1f}X'.format(l, x))
        configs = []

        for config, data in cpi_mean.iteritems():
            for bench, num in data.iteritems():
                print(config)
                configs += [[config, self._get_config_name(config)]]

        for c, name in configs:
            print()
            if o3 in cpi_mean:
                print('CPI Percent Slowdown (Overhead) ({})'.format(name))
                slowdown = ((cpi_mean[c] - cpi_mean[o3]) / cpi_mean[o3])
                p_percent('Min', slowdown.min())
                p_percent('Max', slowdown.max())
                p_percent('Mean', slowdown.mean())

            if inor in cpi_mean:
                speedup = cpi_mean[inor] / (cpi_mean[inor] - cpi_mean[c])
                print('CPI Percent Speedup ({})'.format(name))
                p_percent('Min', speedup.min())
                p_percent('Max', speedup.max())
                p_percent('Mean', speedup.mean())

                times = cpi_mean[inor] / cpi_mean[c]
                print('CPI Times Faster ({})'.format(name))
                p_times('Min', times.min())
                p_times('Max', times.max())
                p_times('Mean', times.mean())

            if o3 in cpi_mean:
                gap = ((cpi_mean[inor] - cpi_mean[c]) / (cpi_mean[inor] - cpi_mean[o3]))
                print('CPI Percent Gap Closed ({})'.format(name))
                p_percent('Min', gap.min())
                p_percent('Max', gap.max())
                p_percent('Mean', gap.mean())
