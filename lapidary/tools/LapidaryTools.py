from argparse import ArgumentParser

from lapidary.config import LapidaryConfig

class ToolDecorator:
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
        # add some help arguments
        LapidaryConfig.add_config_help_arguments(parser)
        # add parser args
        subparsers = self.parser.add_subparsers()

        for cmd_name, arg_add_fn in self:
            cmd = subparsers.add_parser(cmd_name)
            run_fn = arg_add_fn(cmd)
            cmd.set_defaults(fn=run_fn)
    
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
        import inspect
        fns = inspect.getmembers(self, inspect.isfunction)
        for fname, fn in fns:
            if hasattr(fn, '__wrapped__') and fn.__wrapped__:
                yield fn.command_name, fn

    def parse_args(self):
        return self.parser.parse_args()