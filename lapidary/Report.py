#! /usr/bin/env python3
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
import re

import Utils
from SpecBench import *
from Graph import Grapher
from NDAGrapher import NDAGrapher
from NDADataObject import NDADataObject

import pandas as pd
pd.set_option('display.float_format', lambda x: '%.3f' % x)
#pd.set_option('display.max_rows', None)

from Results import *

class Report:
    ''' Aggregrate Results into a unified document. '''

    CHECKPOINT_REGEX = re.compile(r'([0-9]+\.[a-zA-Z]+_r)_(.*)_([0-9]+)_check\.cpt.*')

    def __init__(self, args):
        ''' Gather the summary files from sim results. '''
        if args.simresult_dir is None:
            raise Exception('Must give valid simresult dir as an argument (not None)!')
        res_dir = Path(args.simresult_dir)
        assert res_dir.exists()

        self.verbatim = args.verbatim
        self.do_intersection = not args.include_all

        files = []
        present = defaultdict(lambda: defaultdict(dict))
        self.summary_data  = []
        for dirent in Utils.get_directory_entries_by_time(res_dir):

            if dirent.is_file() and 'summary.json' in dirent.name:
                try:
                    with dirent.open('r') as f:
                        self.summary_data += [json.load(f)]
                except:
                    print('Could not open {}'.format(str(dirent)))


        # benchmark -> configs -> dict{ checkpoint -> series }
        self.sim_series = defaultdict(lambda: defaultdict(dict))
        for summary in self.summary_data:
            if 'checkpoints' not in summary:
                # Means the run was terminated early
                continue

            chk_prefix = '{}_{}'.format(summary['bench'], summary['mode'])
            result_dirs = {}
            for c, status in summary['checkpoints'].items():
                chk_name = Path(c).name
                try:
                    num = int(chk_name.split('_')[0])
                except:
                    continue
                if status == 'successful':
                    result_dirs[num] = res_dir / '{}_{}'.format(chk_prefix, chk_name)

            for checkpoint_num, dirent in result_dirs.items():
                if not dirent.exists():
                    present[benchmark][mode][checkpoint_num] = 0
                    continue

                benchmark       = summary['bench']
                mode            = summary['mode']

                f = dirent / 'res.json'
                if f.exists():
                    files += [f]
                    present[benchmark][mode][checkpoint_num] = 1

                    try:
                        series = pd.read_json(f, typ='series')
                        self.sim_series[benchmark][mode][checkpoint_num] = series
                    except:
                        present[benchmark][mode][checkpoint_num] = 0

                else:
                    present[benchmark][mode][checkpoint_num] = 0

            present_list = defaultdict(lambda: defaultdict(list))
            for benchmark_name, per_config in present.items():
                for config_name, checkpoint_mappings in per_config.items():
                    checkpoints = sorted(checkpoint_mappings.keys())
                    num_checkpoints = summary['total_checkpoints']

                    for i in range(num_checkpoints):
                        present_list[benchmark_name][config_name] += \
                            [ present[benchmark_name][config_name][i]
                                if i in present[benchmark_name][config_name]
                                else 0 ]

        if len(files) == 0:
            raise Exception('No valid result files in given directory!.')
        self.outfile = args.output_file
        self.files = files
        self.present = present_list

    def _get_all_results(self):
        all_res = []
        for f in self.files:
            with f.open() as fd:
                results_obj = json.load(fd)
                all_res += [results_obj]
        print('Collected results from {} files.'.format(len(self.files)))

        res_by_type = defaultdict(lambda: defaultdict(list))

        for res in all_res:
            assert RunType.__name__ in res and 'benchmark' in res
            t = res[RunType.__name__]
            b = res['benchmark']
            res_by_type[t][b] += [res]

        return res_by_type

    def _construct_data_frames(self):
        '''
        I want the following:

        Per benchmark:
                           stat1   stat2   stat3
            config_name:     val     val     val
        '''

        self.sim_data_frames = defaultdict(dict)
        for benchmark, config_series in self.sim_series.items():

            checkpoint_sets = []
            for config_name, checkpoint_results in config_series.items():
                checkpoint_sets.append(checkpoint_results.keys())

            all_checkpoints = set(checkpoint_sets[0])
            if self.do_intersection:
                all_checkpoints.intersection_update(*checkpoint_sets[1:])
                print('{} shares {} checkpoints across all configs.'.format(
                    benchmark, len(all_checkpoints)))
            else:
                print('For {}...'.format(benchmark))
                for config_name, checkpoint_results in config_series.items():
                    print('\t{} has {} checkpoints.'.format(
                        config_name, len(checkpoint_results)))

            only_use = list(all_checkpoints)

            for config_name, checkpoint_results in config_series.items():
                if not self.do_intersection:
                    only_use = [k for k in checkpoint_results.keys()]
                df = pd.DataFrame(checkpoint_results)[only_use].T
                if 'inorder' in config_name:
                    df['MLP'] = pd.Series(list(itertools.repeat(1.0, df.shape[1])))
                    df['avgLatencyToIssue'] = pd.Series(list(itertools.repeat(0.0, df.shape[1])))

                stat_means = df.mean().rename('mean')
                stat_stdev = df.std(ddof=0).rename('std')
                stat_nums  = df.count().rename('count')
                assert stat_nums.min() >= 0
                stat_ci    = ((1.96 * df.std(ddof=0)) / np.sqrt(stat_nums)).rename('ci')
                summary_df = pd.DataFrame([stat_means, stat_stdev, stat_ci, stat_nums])
                if not self.verbatim:
                    if 'inorder' in config_name or 'invisispec' in config_name:
                        if 'MLP' not in summary_df:
                            summary_df['MLP'] = 1.0
                        summary_df = summary_df[Results.IN_ORDER_STAT_NAMES]
                    else:
                        try:
                            summary_df = summary_df[Results.O3_STAT_NAMES]
                        except:
                            for k in Results.O3_STAT_NAMES:
                                print(k, k in summary_df)
                            raise

                self.sim_data_frames[benchmark][config_name] = summary_df

        return self.sim_data_frames

    def _data_frame_json(self):
        json_obj = defaultdict(dict)
        for benchmark, config_data in self.sim_data_frames.items():
            for config_name, df in config_data.items():
                json_obj[benchmark][config_name] = df.to_dict()
        return json_obj

    def process_results(self):
        self._construct_data_frames()
        results      = self._data_frame_json()
        checkpoints  = self.present
        report = {}
        if self.verbatim:
            report = { 'results': results, 'checkpoints': checkpoints }
        else:
            report = { 'results': results }
        with open(self.outfile, 'w') as f:
            json.dump(report, f, indent=4)


################################################################################

def add_args(parser):
    subparsers = parser.add_subparsers()
    # For data aggregation!
    process = subparsers.add_parser('process',
                                    help='Aggregate all simulation results')

    process_fn = lambda args: Report(args).process_results()
    process.add_argument('--simresult-dir', '-d', default='simulation_results',
                         help='Where the res.json files reside.')
    process.add_argument('--output-file', '-o', default='report.json',
                         help='Where to output the report')
    process.add_argument('--verbatim', '-v', default=False, action='store_true',
                         help='Output all stats, not just relevant stats.')
    process.add_argument('--include-all', '-i', default=False, action='store_true',
                         help='Include all results, not just across matching subsets of checkpoints')
    process.set_defaults(fn=process_fn)


    # For summaries!
    summary_fn = lambda args: Grapher(args).output_text(
                            NDADataObject(args.input_file).data_by_benchmark())
    summary = subparsers.add_parser('summary',
                                    help='Display relavant results')
    summary.add_argument('--input-file', '-i', default='report.json',
                         help='Where the aggregations live')
    summary.add_argument('--output-dir', '-d', default='.',
                         help='Where to output the report')
    summary.add_argument('--config', '-c', default='graph_config.yaml',
                         help='What file to use for this dataset.')
    summary.set_defaults(fn=summary_fn)

    # For graphing!
    graph = subparsers.add_parser('graph',
                                  help='Graph from report.json')
    NDAGrapher.add_parser_args_graph(graph)

    # For the paper!
    results = subparsers.add_parser('results',
                                  help='Output results from report.json')
    NDAGrapher.add_parser_args_text(results)

################################################################################

def main():
    parser = ArgumentParser(description='Aggregate results from parallel simulation.')
    add_args(parser)

    args = parser.parse_args()
    args.fn(args)

if __name__ == '__main__':
    exit(main())
