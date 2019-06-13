#! /usr/bin/env python3
from argparse import ArgumentParser
import json
from glob import glob
from pathlib import Path
from pprint import pprint
from subprocess import run

from CooldownConfig import CooldownConfig
from SpecBench import SpecBench, Spec2017Bench

def get_configs(args):
    configs = []
    if args.config_group is not None:
        configs = list(CooldownConfig.get_config_group_names(args.config_group))
        configs += ['inorder']
    elif args.config_name is not None:
        configs = [ c for c in list(CooldownConfig.get_all_config_names()) if args.config_name in c and 'runahead' not in c]
        if len(configs) > 1:
            raise Exception('{} matches too many configs: {}'.format(args.config_name, ' '.join(configs)))
    else:
        configs = list(CooldownConfig.get_config_group_names('grand'))
        configs += ['inorder']

    if len(configs) == 0:
        raise Exception('No valid configs selected!')

    return configs

def get_benchmarks(args):
    benchmarks = Spec2017Bench.BENCHMARKS
    if args.benchmarks is not None:
        benchmarks = args.benchmarks['spec2017']
    return sorted(benchmarks, reverse=args.reverse)

def delete_bad_checkpoints(summary_file):
    import shutil
    count = 0
    with summary_file.open() as f:
        summary = json.load(f)
        for checkpoint, status in summary['checkpoints'].items():
            if 'failed' in status and Path(checkpoint).exists():
                shutil.rmtree(checkpoint)
                count += 1
    print('\tDeleted {} invalid checkpoints'.format(count))

def run_all(args):
    checkpoint_root_dir = Path(args.checkpoint_dir)
    assert checkpoint_root_dir.exists()

    res_root   = Path('simulation_results')
    configs    = get_configs(args)
    benchmarks = get_benchmarks(args)

    for benchmark in benchmarks:
        for config in configs:
            config = config.lower()

            binary_name = Spec2017Bench.BIN_NAMES[benchmark]

            checkpoint_dir = checkpoint_root_dir / '{}_gdb_checkpoints'.format(binary_name)
            if args.force_recreate or not checkpoint_dir.exists():
                print('Generating checkpoints for {}.'.format(benchmark))
                run(['./GDBProcess.py', '--bench', benchmark, '--directory',
                    checkpoint_root_dir])
            else:
                print('Skipping checkpoint generation for {}.'.format(benchmark))

            config_name = config
            if config == 'empty':
                config_name = 'o3'
            elif config != 'inorder':
                config_name = '{}_{}'.format('cooldown', config)

            sim_results = res_root / '{}_{}_summary.json'.format(benchmark, config_name)

            print('Simulating {} with {} config.'.format(
                benchmark, config))
            log_file = '{}_{}_simlog.txt'.format(benchmark, config)
            sim_args = ['./ParallelSim.py', '--bench', benchmark, '-d',
                        str(checkpoint_dir), '--log-file', log_file]

            if args.max_checkpoints is not None:
                sim_args += ['-n', args.max_checkpoints]

            if 'inorder' in config or 'in-order' in config:
                sim_args += ['--in-order']
                config = 'inorder'
            else:
                sim_args += ['--cooldown-config', config]

            run(sim_args)

            for d in checkpoint_dir.iterdir():
                if d.is_dir():
                    stats_file = d / 'stats.txt'
                    if stats_file.exists():
                        stats_file.unlink()

            if sim_results.exists():
                delete_bad_checkpoints(sim_results)

def main():
    parser = ArgumentParser(description='Automate runs across multiple benchmarks')
    parser.add_argument('--benchmarks', '-b', nargs='*',
                        action=SpecBench.ParseBenchmarkNames,
                        help='Which benchmarks to run. If empty, run all.')
    parser.add_argument('--config-group', '-g', nargs='?',
                        help='What config group to run')
    parser.add_argument('--config-name', '-c', nargs='?',
                        help='What single config to run')
    parser.add_argument('--force-recreate', action='store_true',
                        help='Force the recreation of checkpoints')
    parser.add_argument('--force-rerun', action='store_true',
                        help='Resimulate benchmarks which have already run.')
    parser.add_argument('--max-checkpoints', '-m', nargs='?',
                        help='Specify the max number of checkpoints to simulate')
    parser.add_argument('--checkpoint-dir', '-d',
                        help='Checkpoint root directory')
    parser.add_argument('--reverse', action='store_true',
                        help='Reverse benchmark order')

    args = parser.parse_args()

    run_all(args)

if __name__ == '__main__':
    exit(main())
