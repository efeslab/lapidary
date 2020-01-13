from argparse import ArgumentParser
import logging

from lapidary.config import LapidaryConfig

class ToolDecorator:
    '''
        Custom decorator for adding commands to the main lapidary module.
        Make sure to add this as the lowest decorator in the stack, i.e.:

        @staticmethod
        @ToolDecorator

        Otherwise you'll get some fun bugs.
    '''

    def __init__(self, name):
        self.name = name

    def __call__(self, arg_fn):
        def invoke(*vargs, **kwargs):
            return arg_fn(*vargs, **kwargs)
        
        invoke.__wrapped__ = True
        invoke.command_name = self.name
        return invoke

class LapidaryTools:

    def __init__(self, parser):
        self.parser = parser
        self.add_logging_args()
        LapidaryConfig.add_config_arguments(parser)
        # add parser args
        subparsers = self.parser.add_subparsers()

        for cmd_name, arg_add_fn in self:
            cmd = subparsers.add_parser(cmd_name)
            run_fn = arg_add_fn(cmd)
            cmd.set_defaults(fn=run_fn)

    def add_logging_args(self):
        self.parser.add_argument('--log-level', '-l', help='Set level for logging.',
                                 choices=[logging.CRITICAL, logging.ERROR,
                                          logging.WARNING, logging.INFO,
                                          logging.DEBUG, logging.NOTSET])
    
    @staticmethod
    @ToolDecorator("create")
    def add_create_args(parser):
        from lapidary.tools import GDBProcess
        GDBProcess.add_args(parser)

        return lambda args: GDBProcess.main(args)

    @staticmethod
    @ToolDecorator("simulate")
    def add_simulate_args(parser):
        from lapidary.simulate import Experiment
        Experiment.add_experiment_args(parser)

        return lambda args: Experiment.do_experiment(args)

    @staticmethod
    @ToolDecorator("parallel-simulate")
    def add_parallel_simulate_args(parser):
        from lapidary.simulate.ParallelSim import ParallelSim
        ParallelSim.add_args(parser)

        return lambda args: ParallelSim.main(args)

    @staticmethod
    @ToolDecorator("report")
    def add_report_args(parser):
        from lapidary.report.Report import Report
        Report.add_args(parser)

        return lambda args: Report.main(args)

    def __iter__(self):
        '''
            Returns all functions with the __wrapped__ attribute, i.e. all
            of the functions decorated with the ToolDecorator.
        '''
        import inspect
        fns = inspect.getmembers(self, inspect.isfunction)
        for fname, fn in fns:
            if hasattr(fn, '__wrapped__') and fn.__wrapped__:
                yield fn.command_name, fn

    def parse_args(self):
        '''
            Parse configurations and do the basic setup for the logging 
            infrastructure before anything else occurs.
        '''
        return self.parser.parse_args()