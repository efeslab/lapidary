import yaml
from pathlib import Path

from lapidary.utils import gettype

SCHEMA_FILE = Path(__file__).parent / 'schema.yaml'
SCHEMA = ''
with SCHEMA_FILE.open('r') as f:
    SCHEMA = yaml.safe_load(f)

class LapidaryConfig(dict):

    def __init__(self, filename):
        with Path(filename).open('r') as f:
            self.fields = yaml.safe_load(f)

        self.elements = {}
        for field in SCHEMA:
            required = SCHEMA[field]['required']
            ftype = SCHEMA[field]['type']
            if field not in self.fields and required:
                raise Exception('Required field %s is not in %s!' % (field, filename))
            elif field in self.fields:
                element = gettype(ftype)(self.fields[field])
                if isinstance(element, Path):
                    if not element.is_absolute():
                        element = (Path(filename).parent / element).resolve()

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