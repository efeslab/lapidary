from argparse import Action
from pathlib import Path

import logging
import yaml

from lapidary.utils import gettype

from lapidary.config.Gem5FlagConfig import Gem5FlagConfig

SCHEMA_FILE = Path(__file__).parent / 'schema.yaml'
SCHEMA = None

def get_schema():
    global SCHEMA
    if SCHEMA is None:
        with SCHEMA_FILE.open('r') as f:
            SCHEMA = yaml.safe_load(f)
    return SCHEMA

class ConfigException(Exception):
    pass

class LapidaryConfigHelp(Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs['nargs'] = 0
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(yaml.dump(get_schema()))
        exit(0)

class LapidaryConfig(dict):

    def _parse_yaml_data(self, schema, raw_config):
        elements = {}
        for field in schema:
            required = schema[field]['required']
            ftype = schema[field]['type']

            if field not in raw_config and required:
                raise ConfigException('Required field {} is not in {}!'.format(
                    field, filename))
            elif field not in raw_config:
                continue

            element = gettype(ftype)(raw_config[field])
            if isinstance(element, Path):
                if not element.is_absolute() and self.filename is not None:
                    raw_path = Path(self.filename).parent / element
                    element = raw_path.resolve()
            if isinstance(element, dict):
                options = get_schema()[field]['valid_options']
                element = self._parse_yaml_data(options, element)

            elements[field] = element

        return elements    

    def __init__(self, filename=None, rawdata=None):
        assert filename is not None or rawdata is not None
        self.filename = None

        if filename is not None:
            self.filename = filename
            with Path(filename).open('r') as f:
                rawdata = f.read()
            
        raw_config = yaml.safe_load(rawdata)
        if not raw_config:
            raise ConfigException('Empty configuration was provided!')

        parsed_config = self._parse_yaml_data(get_schema(), raw_config)
        try:
            super().__init__(**parsed_config)
        except:
            super(type(self), self).__init__(**parsed_config)
        
        Gem5FlagConfig.parse_plugins(self)


    @classmethod
    def add_config_arguments(cls, parser):
        parser.add_argument('--config', '-c', default='.lapidary.yaml',
                            type=cls,
                            help=('Load simulation configurations from the '
                                  'specified YAML file.'))
        parser.add_argument('--config-help', action=LapidaryConfigHelp,
            help='Show help for construction the configuration file.')

    @classmethod
    def add_optparse_args(cls, parser):
        parser.add_option('--config-file', default='.lapidary.yaml',
                            help=('Load simulation configurations from the '
                                  'specified YAML file.'))

    @staticmethod
    def add_config_help_arguments(parser):
        parser.add_argument('--config-help', action=LapidaryConfigHelp,
            help='Show help for construction the configuration file.')

