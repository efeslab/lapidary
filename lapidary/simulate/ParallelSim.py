import lapidary.simulate.Experiment as Experiment
import lapidary.utils
from lapidary.utils import Utils
from lapidary.config.specbench.SpecBench import *
from lapidary.config import Gem5FlagConfig

import json
import os
import progressbar
import sys, io

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from fcntl import lockf, LOCK_UN, LOCK_EX
from multiprocessing import Process, cpu_count, Lock, Pool
from pathlib import Path, PosixPath
from pprint import pprint
from progressbar import ProgressBar
from subprocess import Popen, PIPE, DEVNULL
from time import time, sleep
from tempfile import TemporaryFile


class ParallelSim:

    def __init__(self, args, append_log_file=False):
        output_dir_parent = Path('simulation_results')
        if not output_dir_parent.exists():
            output_dir_parent.mkdir()

        self.args = args

        mode = 'o3'
        if args.in_order:
            mode = 'inorder'
        # elif args.invisispec:
        #     mode = 'invisispec_{}'.format(args.scheme)
        elif args.flag_config != 'empty':
            mode = args.flag_config

        self.summary_path = output_dir_parent / '{}_{}_summary.json'.format(
            args.bench, mode)

        self.summary = defaultdict(dict)
        if self.summary_path.exists() and not args.force_rerun:
            print('\tLoading existing results.')
            with self.summary_path.open() as f:
                raw_dict = json.load(f)
                for k, v in raw_dict.items():
                    self.summary[k] = v
        elif self.summary_path.exists() and args.force_rerun:
            print('\tIgnoring old summary file to force rerun.')

        self.summary['mode']  = mode
        self.summary['bench'] = args.bench
        self.summary['successful_checkpoints'] = 0
        self.summary['failed_checkpoints']     = 0

        assert args.checkpoint_dir is not None

        chkdir = Path(args.checkpoint_dir)
        dirents = Utils.get_directory_entries_by_time(chkdir)
        if 'checkpoints' in self.summary:
            self.chkpts = [x for x in dirents if x.is_dir()]
            rm_count = 0
            for chk, status in self.summary['checkpoints'].items():
                chk_path = PosixPath(chk)
                if chk_path in self.chkpts and status != 'not run':
                    rm_count += 1
                    self.chkpts.remove(chk_path)
                    if status == 'failed':
                        self.summary['failed_checkpoints'] += 1
                    elif status == 'successful':
                        self.summary['successful_checkpoints'] += 1
                elif chk_path not in self.chkpts and status != 'not run':
                    if status == 'failed':
                        self.summary['failed_checkpoints'] += 1
                    elif status == 'successful':
                        self.summary['successful_checkpoints'] += 1

            print('\tRemoved {} checkpoints from consideration.'.format(rm_count))
        else:
            self.chkpts = [x for x in dirents if x.is_dir()]

        exp_args = {}

        invalid_counter = 0
        # Always update this, for it could change!
        self.summary['total_checkpoints'] = len(self.chkpts)

        self.result_files = {}
        for chkpt in self.chkpts:
            pmem_file = chkpt / 'system.physmem.store0.pmem'
            if not pmem_file.exists():
                invalid_counter += 1
                self.summary['checkpoints'][str(chkpt)] = 'invalid'
                #print('{} -- invalid checkpoint, skipping'.format(str(chkpt)))
                continue
            self.summary['checkpoints'][str(chkpt)] = 'not run'
            output_dir = output_dir_parent / '{}_{}_{}'.format(
                args.bench, mode, str(chkpt.name))
            arg_list = [
                '--bench', args.bench,
                '--suite', args.suite,
                '--warmup-insts', str(args.warmup_insts),
                '--reportable-insts', str(args.reportable_insts),
                '--start-checkpoint', str(chkpt),
                '--output-dir', str(output_dir),
                '--flag-config', str(args.flag_config)]
            if args.in_order:
                arg_list += ['--in-order']
            # if args.invisispec:
            #     arg_list += ['--invisispec', '--scheme', args.scheme]
            exp_args[str(chkpt)] = arg_list

            result_file = output_dir / 'res.json'
            self.result_files[str(chkpt)] = result_file

        if 'invalid_counter' not in self.summary:
            self.summary['invalid_checkpoints'] = invalid_counter

        if invalid_counter == len(self.chkpts):
            raise Exception('No valid checkpoints to simulate with!')
        elif invalid_counter > 0:
            print('Skipping {} invalid checkpoints'.format(invalid_counter))

        self.num_checkpoints = len(exp_args) + self.summary['successful_checkpoints']
        if args.num_checkpoints is not None:
            self.num_checkpoints = min(args.num_checkpoints, self.num_checkpoints)
            if self.num_checkpoints < args.num_checkpoints:
                print('Warning: Requested {} checkpoints, but only {} are available.'.format(
                    args.num_checkpoints, self.num_checkpoints))

        self.all_proc_args = exp_args
        self.max_procs     = int(args.pool_size)
        self.log_file      = args.log_file
        self.append        = append_log_file
        self.timeout_seconds = (60.0 * 60.0)


    def __del__(self):
        ''' 
            On destruction, output summary to summary file, assuming we made 
            if far enough to have created the summary file path.
        '''
        if hasattr(self, 'summary_path'):
            with self.summary_path.open('w') as f:
                json.dump(self.summary, f, indent=4)

    @staticmethod
    def _run_process(experiment_args, log_file, config):
        '''
            Essentially, we want to just run the experiment stuff again.
            So, we pretend like we're running this from scratch.

            This is already a separate process.
        '''
        parser = ArgumentParser()
        Experiment.add_experiment_args(parser)
        args = parser.parse_args(args=experiment_args)   

        prefix = 'lapidary_parallel_simulate'
        with TemporaryFile(mode='w+', prefix=prefix) as out, \
             TemporaryFile(mode='w+', prefix=prefix) as err, \
             open(log_file, 'a') as f:

            sys.stdout = out
            sys.stderr = err
            Experiment.do_experiment(args, config=config)
            out.seek(0)
            err.seek(0)

            try:
                lockf(f, LOCK_EX)
                f.write('-'*80 + os.linesep)
                f.write(' '.join(experiment_args) + os.linesep)
                f.write('STDOUT ' + '-'*40 + os.linesep)
                f.write(out.read())
                f.write('STDERR ' + '-'*40 + os.linesep)
                f.write(err.read())
            finally:
                lockf(f, LOCK_UN)


    def start(self):
        with open(self.log_file, 'w' if not self.append else 'a') as f:
            f.write('*' * 80 + '\n')
            f.write('Starting simulation run at {}...\n'.format(datetime.utcnow()))

        widgets = [
                    progressbar.Percentage(),
                    ' (', progressbar.Counter(), ' of {})'.format(self.num_checkpoints),
                    ' ', progressbar.Bar(left='[', right=']'),
                    ' ', progressbar.Timer(),
                    ' ', progressbar.ETA(),
                  ]
        with Pool(self.max_procs) as pool, \
             ProgressBar(widgets=widgets, max_value=self.num_checkpoints) as bar:

            bar.start()

            wait_time = 0.001
            failed_counter        = 0
            successful_counter    = self.summary['successful_checkpoints']
            failed_counter        = self.summary['failed_checkpoints']
            remaining_checkpoints = len(self.all_proc_args)
            tasks = {}
            task_results = {}
            task_checkpoint = {}

            def do_visual_update(self):
                counter = min(successful_counter, self.num_checkpoints)
                bar.update(counter)

            self.__class__.do_visual_update = do_visual_update

            while successful_counter < self.num_checkpoints and \
                  remaining_checkpoints > 0:

                needed_checkpoints = self.num_checkpoints - successful_counter
                proc_args = Utils.select_evenly_spaced(self.all_proc_args, needed_checkpoints)

                for chkpt in proc_args:
                    assert chkpt in self.all_proc_args
                    del self.all_proc_args[chkpt]
                remaining_checkpoints = len(self.all_proc_args)

                for chkpt, experiment_args in proc_args.items():
                    fn_args = (experiment_args, self.log_file, self.args.config)
                    task = pool.apply_async(ParallelSim._run_process, fn_args)

                    tasks[task] = time()
                    task_results[task] = self.result_files[chkpt]
                    task_checkpoint[task] = chkpt

                finished_tasks = []
                done_waiting = False
                while not done_waiting:
                    done_waiting = True
                    successful   = False
                    max_time     = 0.0
                    for task, start_time in tasks.items():
                        task.wait(wait_time)
                        if task.ready():
                            # This re-raises any exceptions.
                            task.get()
                            successful      = True
                            finished_tasks += [task]
                            result_file     = task_results.pop(task)
                            checkpoint      = task_checkpoint.pop(task)
                            if not result_file.exists():
                                failed_counter += 1
                                self.summary['checkpoints'][checkpoint] = 'failed'
                            else:
                                successful_counter += 1
                                self.summary['checkpoints'][checkpoint] = 'successful'
                        elif successful:
                            done_waiting = False
                            tasks[task] = time()
                        else:
                            done_waiting = False
                            max_time = max(time() - start_time, max_time)

                    tasks = {t:s for t, s in tasks.items() if t not in finished_tasks}
                    if not successful and max_time > self.timeout_seconds:
                        done_waiting = True
                    if len(tasks) == 0:
                        done_waiting = True
                    if successful_counter >= self.num_checkpoints:
                        done_waiting = True

                    self.do_visual_update()

            # Now we're waiting on straggler processes
            ready_to_terminate = successful_counter >= self.num_checkpoints
            while not ready_to_terminate:
                ready_to_terminate = True
                finished_tasks = []
                for task, start_time in tasks.items():
                    successful = False
                    task.wait(wait_time)
                    if task.ready():
                        successful = True
                        # Only terminate if completely stagnant
                        ready_to_terminate = False
                        finished_tasks += [task]
                        result_file = task_results.pop(task)
                        checkpoint  = task_checkpoint.pop(task)
                        if not result_file.exists():
                            failed_counter += 1
                            self.summary['checkpoints'][checkpoint] = 'failed'
                        else:
                            successful_counter += 1
                            self.summary['checkpoints'][checkpoint] = 'successful'
                    elif time() - start_time < self.timeout_seconds:
                        ready_to_terminate = False
                    else:
                        finished_tasks += [task]
                        result_file = task_results.pop(task)
                        checkpoint  = task_checkpoint.pop(task)
                        failed_counter += 1
                        self.summary['checkpoints'][checkpoint] = 'failed (timeout)'


                tasks = {t:s for t, s in tasks.items() if t not in finished_tasks}
                self.do_visual_update()

            self.summary['successful_checkpoints'] = successful_counter
            self.summary['failed_checkpoints']     = failed_counter


    @staticmethod
    def add_args(parser):
        # SpecBench.add_parser_args(parser)
        Experiment.add_experiment_args(parser)
        # Gem5FlagConfig.add_parser_args(parser)

        parser.add_argument('--checkpoint-dir', '-d',
                            help='Locations of all the checkpoints')
        parser.add_argument('--pool-size', '-p', default=cpu_count(),
                            help='Number of threads to use')
        parser.add_argument('--log-file', '-l', 
            default='parallel_simulation_log_{}.txt'.format(
                datetime.now().isoformat(sep='_', timespec='seconds')),
                            help=('Where to log stdout/stderr from experiment runs. '
                            'Defaults to parallel_simulation_log_<time>.txt'))
        parser.add_argument('--num-checkpoints', '-n', default=None, type=int,
            help='Number of checkpoints to simulate. If None, then all.')
        parser.add_argument('--all-configs', action='store_true',
            help='Run parallel sim for all configurations')
        parser.add_argument('--force-rerun', action='store_true',
            help='Ignore previous summary files and rerun from scratch')

    @classmethod
    def main(cls, args):
        # parser = ArgumentParser(description='Run a pool of experiments on gem5.')
        # cls.add_args(parser)

        # args = parser.parse_args()
        # SpecBench.maybe_display_spec_info(args)
        # CooldownConfig.maybe_show_configs(args)

        benchmarks = SpecBench.get_benchmarks(args)

        if len(benchmarks) != 1:
            raise Exception(
                    'For now, ParallelSim only supports one benchmark at a time.')

        benchmark = benchmarks[0]

        print('ParallelSim for {}'.format(benchmark))
        args.bench = benchmark
        if args.all_configs or args.flag_config_group is not None:
            config_names = CooldownConfig.get_all_config_names() \
                            if args.all_configs \
                            else CooldownConfig.get_config_group_names(args.config_group)
            # Run In-Order:
            args.in_order = True
            print('In-order simulation')
            sim = ParallelSim(args)
            sim.start()
            # Run everything else:
            args.in_order = False
            for flag_config_name in config_names:
                if flag_config_name == 'default':
                    print('Skipping default configuration')
                    continue
                if flag_config_name == 'empty':
                    print('Out-of-order simulation')
                else:
                    print('Cooldown config {} simulation'.format(flag_config_name))
                args.flag_config = flag_config_name
                sim = ParallelSim(args, append_log_file=True)
                sim.start()

        else:
            try:
                sim = cls(args)
                sim.start()
            except Exception as e:
                print('Could not start simulations:', e)
                return 1

        return 0