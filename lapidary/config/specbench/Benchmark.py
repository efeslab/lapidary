from pathlib import Path

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
