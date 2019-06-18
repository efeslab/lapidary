from argparse import ArgumentParser
from inspect import isclass
from pprint import pprint

class Gem5FlagConfig:

    class Empty:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            pass

    # Maps group name to list of classes
    GROUPS = {
            'Empty': [Empty]
    }

    @staticmethod
    def add_parser_args(parser):
        parser.add_argument('--cooldown-config', default='empty',
            help='Enable Cooldown with a specific variant')
        parser.add_argument('--config-group', default=None,
            help='Run a specific group of configs (plus in order and OOO')
        parser.add_argument('--list-configs', action='store_true', default=False,
            help='Show available configs')
        parser.add_argument('--list-groups', action='store_true', default=False,
            help='Show available groups')

    @staticmethod
    def add_optparse_args(parser):
        parser.add_option('--cooldown-config', default='empty',
            help='Enable Cooldown with a specific variant')

    @classmethod
    def _get_config_classes(cls):
        return { k.lower(): v for k, v in cls.__dict__.items() if isclass(v) }

    @classmethod
    def _get_config_groups(cls):
        return { k.lower(): v for k, v in cls.GROUPS.items() }

    @classmethod
    def is_valid_config(cls, config_name):
        config_name = config_name.lower()
        return config_name in cls._get_config_classes()

    @classmethod
    def get_all_config_names(cls):
        config_classes = cls._get_config_classes()
        return [ name for name in config_classes ]

    @classmethod
    def get_config(cls, config_name):
        config_name = config_name.lower()
        print('Config: {}'.format(config_name))

        config_classes = cls._get_config_classes()
        if config_name not in config_classes:
            raise Exception('{} not a valid config. Valid configs: {}'.format(
              config_name, ', '.join(config_classes.keys())))

        config_class = config_classes[config_name]
        config_methods = { k: v for k, v in
            config_class.__dict__.items() if isinstance(v, staticmethod)}

        before_init_fn = config_methods['before_init'].__func__
        after_warmup_fn = config_methods['after_warmup'].__func__
        return before_init_fn, after_warmup_fn

    @classmethod
    def get_config_group_names(cls, group_name):
        group_name = group_name.upper()
        for group, classes in cls.GROUPS.items():
            if group_name in group:
                for config_class in classes:
                    yield config_class.__name__

    @classmethod
    def maybe_show_configs(cls, args):
        do_exit = False
        if args.list_configs:
            do_exit = True
            pprint([k for k in cls._get_config_classes().keys()])
        if args.list_groups:
            do_exit = True
            pprint([k for k in cls._get_config_groups().keys()])

        if do_exit:
            exit()

