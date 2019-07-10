from argparse import ArgumentParser, Action
from inspect import isclass
from pprint import pprint

from lapidary.config.LapidaryConfig import LapidaryConfig, ConfigException

from lapidary.config.FlagConfigure import FlagConfigure, EmptyConfig

class Gem5FlagConfig:

    CONFIGS = {
        'Empty': EmptyConfig,
    }

    # Maps group name to list of classes
    GROUPS = {
        'Empty': [EmptyConfig]
    }

    @classmethod
    def parse_plugins(cls, config):
        assert isinstance(config, LapidaryConfig)

        if 'gem5_flag_config_plugin' not in config:
            return

        from importlib.util import spec_from_file_location, module_from_spec

        module_path = config['gem5_flag_config_plugin']
        module_name = module_path.name.split('.')[0]

        spec = spec_from_file_location(module_name, module_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Now, extract all the classes
        import inspect

        classes = [p[1] for p in inspect.getmembers(module) if inspect.isclass(p[1])]
        subs = [c for c in classes if issubclass(c, FlagConfigure) and c != FlagConfigure]

        if not subs:
            raise ConfigException(f'Module {module} did not contain any FlagConfigure classes!')

        cls.GROUPS[module.__name__] = subs

        for s in subs:
            cls.CONFIGS[s.__name__] = s
            cls.GROUPS[s.__name__] = [s]

    @classmethod
    def _get_config_classes(cls):
        return { k.lower(): v for k, v in cls.CONFIGS.items() }

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

    # Parser arguments
    @classmethod
    def _get_help_class(cls):
        class Gem5FlagConfigHelp(Action):
            def __init__(self, option_strings, dest, **kwargs):
                kwargs['nargs'] = 0
                assert len(option_strings) == 1
                self.do_configs = False
                self.do_groups = False
                if 'configs' in option_strings[0]:
                    self.do_configs = True
                elif 'groups' in option_strings[0]:
                    self.do_groups = True
                else:
                    raise Exception('Invalid use of help command!')
                super().__init__(option_strings, dest, **kwargs)

            def __call__(self, parser, namespace, values, option_string=None):
                config = LapidaryConfig.get_config(namespace)
                cls.parse_plugins(config)

                if self.do_configs:
                    pprint([k for k in cls._get_config_classes().keys()])
                if self.do_groups:
                    for g, m in cls._get_config_groups().items():
                        print(f'{g}:')
                        pprint([c.__name__ for c in m])
                        print()
                exit(0)
        
        return Gem5FlagConfigHelp


    @classmethod
    def add_parser_args(cls, parser):
        parser.add_argument('--flag-config', default='empty',
            help='Use a debug flag configuration setting')
        parser.add_argument('--flag-config-group', default=None,
            help='Run a specific group of configs (plus in order and OOO)')
        parser.add_argument('--list-configs', action=cls._get_help_class(),
            help='Show available configs')
        parser.add_argument('--list-groups', action=cls._get_help_class(),
            help='Show available groups')

    @staticmethod
    def add_optparse_args(parser):
        parser.add_option('--flag-config', default='empty',
            help='Use a debug flag configuration setting')
