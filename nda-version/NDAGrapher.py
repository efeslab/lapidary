from argparse import ArgumentParser
from collections import defaultdict
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
from NDADataObject import NDADataObject

import pandas as pd

class NDAGrapher:

    def __init__(self, args):
        self.args = args
        self.data = NDADataObject(Path(args.input_file))
        if 'schema_file' in args:
            self.output_dir = Path(args.output_dir)
            self.schema_file = Path(args.schema_file)
            assert self.schema_file.exists() and self.output_dir.exists()
            with self.schema_file.open() as f:
                self.schema_config = yaml.safe_load(f)
                self.schemas = self.schema_config['schemes']
                assert args.schema_name in self.schemas
                self.schema = self.schemas[args.schema_name]
                self.schema_name = args.schema_name
                self.config_sets = self.schema_config['config_sets']

    def _plot_single_stat(self, gs, layout):
        grapher = Grapher(self.args)

        dfs = self.data.data_by_benchmark()
        options = layout['options']

        config_set = layout['config_set'] if 'config_set' in layout else 'default'
        dfs = self.data.filter_configs(self.config_sets[config_set], dfs)
        if 'benchmarks' in layout:
            dfs = self.data.filter_benchmarks(layout['benchmarks'], dfs)
        dfs = self.data.reorder_data_frames(dfs)
        dfs = self.data.filter_stats(layout['stat'], dfs)

        means_df = None
        ci_df = None
        flush = True
        if 'average' in options and options['average']:
            dfs = self.data.average_stats(dfs)
            flush = True
            means_df = pd.DataFrame({'Average': dfs.T['mean']}).T
            ci_df = pd.DataFrame({'Average': dfs.T['ci']}).T
        else:
            means_df = self.data.filter_stat_field('mean', dfs)
            ci_df = self.data.filter_stat_field('ci', dfs)

            if 'benchmarks' in layout and 'Average' in layout['benchmarks']:
                # Also add an average bar:
                dfs = self.data.data_by_benchmark()
                dfs = self.data.filter_configs(self.config_sets[config_set], dfs)
                dfs = self.data.reorder_data_frames(dfs)
                dfs = self.data.filter_stats(layout['stat'], dfs)
                avg_dfs = self.data.average_stats(dfs)
                avg_mean = avg_dfs.T['mean']
                ci_zero = avg_mean.copy()
                ci_zero[:] = 0
                means_df = means_df.append(pd.DataFrame({'Average': avg_mean}).T)
                ci_df = ci_df.append(pd.DataFrame({'Average': ci_zero}).T)
                flush = True

        if 'benchmarks' in layout:
            means_df = means_df.reindex(layout['benchmarks'])
            ci_df = ci_df.reindex(layout['benchmarks'])

        return grapher.graph_single_stat(means_df, ci_df, gs,
                                         flush=flush, **options)

    def _plot_cpi_breakdown(self, gs, layout):
        grapher = Grapher(self.args)

        dfs = self.data.data_by_benchmark()
        config_set = layout['config_set'] if 'config_set' in layout else 'default'
        dfs = self.data.filter_configs(self.config_sets[config_set], dfs)
        final_dfs = self.data.calculate_cpi_breakdown(dfs)

        options = layout['options']
        if 'average' in options and options['average']:
            final_dfs = self.data.calculate_cpi_breakdown_avg(dfs)
            mi_tuples = [('Average', i) for i in final_dfs.index]
            final_dfs.index = pd.MultiIndex.from_tuples(mi_tuples)

        return grapher.graph_grouped_stacked_bars(final_dfs, gs, **options)

    def output_relevant_stats(self):
        p_percent = lambda l, x: print('\t--- {0}: {1:.1f}%'.format(l, x * 100.0))
        p_times = lambda l, x: print('\t--- {0}: {1:.1f}X'.format(l, x))
        p_raw = lambda l, x: print('\t--- {0}: {1:.2f}'.format(l, x))

        grapher = Grapher(self.args)
        dfs = self.data.data_by_config()

        brk_dfs = self.data.calculate_cpi_breakdown_avg(self.data.data_by_benchmark())
        #brk_avg_df = brk_dfs.mean(level=1).T
        brk_avg_df = brk_dfs.T

        assert 'o3' in dfs and 'inorder' in dfs and 'o3' in brk_avg_df
        def get_avg(df):
            a_dict = self.data.reorder_data_frames(df)
            a_df = {}
            for k, v in a_dict.items():
                a_df[k] = pd.DataFrame(v).T
            b_df = self.data.average_stats(a_df)
            return b_df.T['mean']

        o3_stats = get_avg(dfs['o3'])
        o3_brkdn = brk_avg_df['o3']
        io_stats = get_avg(dfs['inorder'])

        brkdn_ratio = lambda series, s: (series[s] / series.sum())

        configs = []
        for config in dfs.keys():
            if config != 'o3' and config != 'inorder':
                configs += [[config, grapher._get_config_name(config)]]

        backend_stall_added = {}
        frontend_stall_added = {}
        cycle_to_issue_added = {}
        commit = {}

        print('OoO:')
        p_raw('CPI', o3_stats['cpi'])
        p_percent('Backend Stalls', o3_brkdn['Backend Stalls'])
        p_percent('Commit', o3_brkdn['Commit'])
        print('In-Order CPI: ')
        p_raw('Mean', io_stats['cpi'])

        for c, name in configs:
            config_stats = get_avg(dfs[c])
            config_brkdn = brk_avg_df[c]

            print('Stats for Config: {}'.format(name))
            p_raw('CPI', config_stats['cpi'])

            print('\tCPI Percent Slowdown (Overhead)')
            slowdown = ((config_stats['cpi'] - o3_stats['cpi']) / o3_stats['cpi'])
            p_percent('Mean', slowdown)

            speedup = io_stats['cpi'] / (io_stats['cpi'] - config_stats['cpi'])
            print('\tCPI Percent Speedup')
            p_percent('Mean', speedup)

            times = io_stats['cpi'] / config_stats['cpi']
            print('\tCPI Times Faster')
            p_times('Mean', times)

            gap = ((io_stats['cpi'] - config_stats['cpi']) / (io_stats['cpi'] - o3_stats['cpi']))
            print('\tCPI Percent Gap Closed')
            p_percent('Mean', gap)

            if 'Invisispec' not in name:
                added = config_brkdn['Backend Stalls'] - o3_brkdn['Backend Stalls']
                backend_stall_added[name] = added
                added = config_brkdn['Frontend Stalls'] - o3_brkdn['Frontend Stalls']
                frontend_stall_added[name] = added
                commit[name] = config_brkdn['Commit'] - o3_brkdn['Commit']

            if 'avgLatencyToIssue' in config_stats and 'cycle delay' not in name\
                    and 'Invisispec' not in name:
                cti_added = config_stats['avgLatencyToIssue'] - o3_stats['avgLatencyToIssue']
                cycle_to_issue_added[name] = cti_added


        print('='*80)
        import operator

        backend_max = max(backend_stall_added.items(), key=operator.itemgetter(1))
        print('Max backend stalls added:')
        p_percent(*backend_max)

        backend_min = min(backend_stall_added.items(), key=operator.itemgetter(1))
        print('Min backend stalls added:')
        p_percent(*backend_min)

        frontend_max = max(frontend_stall_added.items(), key=operator.itemgetter(1))
        print('Max frontend stalls added:')
        p_percent(*frontend_max)

        frontend_min = min(frontend_stall_added.items(), key=operator.itemgetter(1))
        print('Min frontend stalls added:')
        p_percent(*frontend_min)

        commit_max = max(commit.items(), key=operator.itemgetter(1))
        print('Max commit:')
        p_percent(*commit_max)

        commit_min = min(commit.items(), key=operator.itemgetter(1))
        print('Min commit:')
        p_percent(*commit_min)

        backend_max = max(cycle_to_issue_added.items(), key=operator.itemgetter(1))
        print('Max cycles to issue added:')
        p_raw(*backend_max)

        backend_min = min(cycle_to_issue_added.items(), key=operator.itemgetter(1))
        print('Min cycle to issue added:')
        p_raw(*backend_min)


    def plot_schema(self):
        grapher = Grapher(self.args)

        dimensions = self.schema['dimensions']

        artists = []
        for layout_config in self.schema['plots']:
            width = layout_config['size'][0]
            height = layout_config['size'][1]
            axis = plt.subplot2grid(dimensions, layout_config['pos'],
                                    rowspan=width, colspan=height)

            if layout_config['type'] == 'single_stat':
                a = self._plot_single_stat(axis, layout_config)
                artists += [a]
            elif layout_config['type'] == 'cpi_breakdown':
                artists += self._plot_cpi_breakdown(axis, layout_config)

        plt.subplots_adjust(wspace=0.05, hspace=0.0)

        fig = plt.gcf()
        print_size = self.schema['print_size']
        fig.set_size_inches(*print_size)
        fig.tight_layout()

        output_file = str(self.output_dir / self.schema['file_name'])
        plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0.02,
                    additional_artists=artists)
        plt.close()

    @classmethod
    def add_parser_args_graph(cls, parser):
        parser.add_argument('--input-file', '-i', default='report.json',
                            help='Where the aggregations live')
        parser.add_argument('--output-dir', '-d', default='.',
                            help='Where to output the report')
        parser.add_argument('--config', '-c', default='graph_config.yaml',
                            help='What file to use for this dataset.')

        parser.add_argument('--schema-file', default='graph_schemes.yaml',
                            help='File containing relevant schemas.')
        parser.add_argument('--filter', '-f', default=None, nargs='+',
                            help='what benchmarks to filter, all if None')
        parser.add_argument('schema_name', help='Name of the schema to use.')
        graph_schema_fn = lambda args: cls(args).plot_schema()
        parser.set_defaults(fn=graph_schema_fn)

    @classmethod
    def add_parser_args_text(cls, parser):
        parser.add_argument('--input-file', '-i', default='report.json',
                            help='Where the aggregations live')
        parser.add_argument('--output-dir', '-d', default='.',
                            help='Where to output the report')
        parser.add_argument('--config', '-c', default='graph_config.yaml',
                            help='What file to use for this dataset.')
        parser.add_argument('--filter', '-f', default=None, nargs='+',
                            help='what benchmarks to filter, all if None')
        text_schema_fn = lambda args: cls(args).output_relevant_stats()
        parser.set_defaults(fn=text_schema_fn)
