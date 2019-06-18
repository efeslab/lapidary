import yaml
from pathlib import Path

from lapidary.utils import gettype

SCHEMA_FILE = Path(__file__).parent / 'schema.yaml'
SCHEMA = ''
with SCHEMA_FILE.open('r') as f:
    SCHEMA = yaml.safe_load(f)

class ConfigException(Exception):
    pass

class LapidaryConfig(dict):

    def __init__(self, filename=None, rawdata=None):
        assert filename is not None or rawdata is not None
        self.filename = None

        if filename is not None:
            self.filename = filename
            with Path(filename).open('r') as f:
                rawdata = f.read()
            
        self.fields = yaml.safe_load(rawdata)
        if not self.fields:
            raise ConfigException('Empty configuration was provided!')
        self._parse_yaml_data()

    def _parse_yaml_data(self):
        self.elements = {}
        for field in SCHEMA:
            required = SCHEMA[field]['required']
            ftype = SCHEMA[field]['type']
            if field not in self.fields and required:
                raise ConfigException(f'Required field {field} is not in {filename}!')
            elif field in self.fields:
                element = gettype(ftype)(self.fields[field])
                if isinstance(element, Path):
                    if not element.is_absolute() and self.filename is not None:
                        raw_path = Path(self.filename).parent / element
                        element = raw_path.resolve()
                if isinstance(element, dict):
                    options = SCHEMA[field]['valid_options']
                    for option, typestr in options.items():
                        element[option] = gettype(typestr)(element[option])

                self.elements[field] = element

        super().__init__(**self.elements)

    @staticmethod
    def add_config_arguments(parser):
        parser.add_argument('--config', '-c', 
                            help=('Load simulation configurations from the '
                                  'specified YAML file.'))

    @classmethod
    def get_config(cls, args):
        return cls(args.config)