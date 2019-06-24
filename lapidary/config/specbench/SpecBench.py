from lapidary.config.specbench.Spec2017Bench import *

from argparse import Action
from collections import defaultdict
from enum import Enum
from pathlib import Path
from pprint import pprint
import itertools
import os
import shutil

class Benchmark:
    def __init__(self, binary, args, outfile=None):
        assert isinstance(binary, Path)
        assert isinstance(args, list)
        assert isinstance(outfile, Path) or outfile is None
        self.binary = binary
        self.args = args
        self.outfile = outfile

    def to_se_args(self):
        args = [
            '--cmd', str(self.binary),
            '--options', ' '.join(self.args)
            ]
        return args

    def __repr__(self):
        pass

class SpecBench:
    SPEC2017 = 'spec2017'
    SUITES   = {SPEC2017: Spec2017Bench}

    class ParseBenchmarkNames(Action):
        def __init__(self, option_strings, dest, nargs='+', **kwargs):
            super().__init__(option_strings, dest, nargs=nargs, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            all_possible = defaultdict(list)
            for value in values:
                for suite, cls in SpecBench.SUITES.items():
                    for benchmark in cls.BENCHMARKS:
                        if value in benchmark:
                            all_possible[suite] += [benchmark]

            setattr(namespace, self.dest, all_possible)

    class ListAction(Action):
        def __init__(self, option_strings, dest, **kwargs):
            kwargs['nargs'] = 0
            super().__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string):
            for suite in SpecBench.SUITES:
                num_bench = len(SpecBench.SUITES[suite].BENCHMARKS)
                print(f'SPEC CPU suite {suite} has {num_bench} benchmarks:')
                pprint(SpecBench.SUITES[suite].BENCHMARKS)
            exit(0)

    # def __init__(self, bin_dir=Path('bin'), input_dir=Path('data')):
    #     self.bin_dir = bin_dir
    #     self.input_dir = input_dir

    def __init__(self, config):
        assert 'spec2017_config' in config
        self.spec_config = config['spec2017_config']

    def create(self, suite_name, bench_name, input_type):
        print("Hello!")
        assert suite_name in SpecBench.SUITES
        spec_cls = SpecBench.SUITES[suite_name]
        specsuite = spec_cls(self.spec_config['spec2017_src_path'], 
                             self.spec_config['workspace_path'])
        
        return specsuite.create(bench_name, input_type)

    @classmethod
    def add_parser_args(cls, parser):
        parser.add_argument('--bench', action=cls.ParseBenchmarkNames,
                            help='Run a benchmark(s) from SPEC', nargs='+')
        parser.add_argument('--suite',
                            help='Which SPEC suite to use. Default is 2017',
                            default='spec2017', nargs='?')
        parser.add_argument('--input-type',
                            help='Which SPEC input type to use. Default is refrate',
                            default='refrate', nargs='?')
        parser.add_argument('--list-bench',
                            help='List which benchmarks are available for what suite and exit',
                            action=cls.ListAction)

    @classmethod
    def get_benchmarks(cls, args):
        if len(args.bench) == 0:
            raise Exception('No benchmarks match specified option.')
        if len(args.bench[args.suite]) == 0:
            raise Exception('No such benchmark in specified suite!')
        return args.bench[args.suite]
