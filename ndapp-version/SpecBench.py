from argparse import Action
from collections import defaultdict
from enum import Enum
from pathlib import Path
from pprint import pprint
import itertools
import os
import shutil

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

################################################################################

class Spec2006Bench:
    class Benchmarks(Enum):
        PHONY = 'phony'

    BENCHMARKS = [b.value for b in Benchmarks]


class Spec2017Bench:
    class Benchmarks(Enum):
        PERL      = '500.perlbench_r'
        GCC       = '502.gcc_r'
        BWAVES    = '503.bwaves_r'
        MCF       = '505.mcf_r'
        CACTUS    = '507.cactuBSSN_r'
        NAMD      = '508.namd_r'
        PAREST    = '510.parest_r'
        POVRAY    = '511.povray_r'
        LBM       = '519.lbm_r'
        OMNETPP   = '520.omnetpp_r'
        WRF       = '521.wrf_r'
        XALAN     = '523.xalancbmk_r'
        X264      = '525.x264_r'
        BLENDER   = '526.blender_r'
        CAM4      = '527.cam4_r'
        DEEPSJENG = '531.deepsjeng_r'
        IMAGICK   = '538.imagick_r'
        LEELA     = '541.leela_r'
        NAB       = '544.nab_r'
        EXCHANGE2 = '548.exchange2_r'
        FOTONIK3D = '549.fotonik3d_r'
        ROMS      = '554.roms_r'
        XZ        = '557.xz_r'


    BENCHMARKS = [b.value for b in Benchmarks]
    BIN_NAMES = {
        Benchmarks.PERL.value:         'perlbench_r',
        Benchmarks.GCC.value:          'cpugcc_r',
        Benchmarks.BWAVES.value:       'bwaves_r',
        Benchmarks.MCF.value:          'mcf_r',
        Benchmarks.CACTUS.value:       'cactusBSSN_r',
        Benchmarks.NAMD.value:         'namd_r',
        Benchmarks.PAREST.value:       'parest_r',
        Benchmarks.POVRAY.value:       'povray_r',
        Benchmarks.LBM.value:          'lbm_r',
        Benchmarks.OMNETPP.value:      'omnetpp_r',
        Benchmarks.WRF.value:          'wrf_r',
        Benchmarks.XALAN.value:        'cpuxalan_r',
        Benchmarks.X264.value:         'x264_r',
        Benchmarks.BLENDER.value:      'blender_r',
        Benchmarks.CAM4.value:         'cam4_r',
        Benchmarks.DEEPSJENG.value:    'deepsjeng_r',
        Benchmarks.IMAGICK.value:      'imagick_r',
        Benchmarks.LEELA.value:        'leela_r',
        Benchmarks.NAB.value:          'nab_r',
        Benchmarks.EXCHANGE2.value:    'exchange2_r',
        Benchmarks.FOTONIK3D.value:    'fotonik3d_r',
        Benchmarks.ROMS.value:         'roms_r',
        Benchmarks.XZ.value:           'xz_r'
      }
    INPUT_TYPES = ['refrate', 'refspeed', 'test', 'train']

    # Args
    # - Files consumed as arguments
    INPUT_FILES = {
        Benchmarks.PERL.value:      ['checkspam.pl'],
        Benchmarks.GCC.value:       ['ref32.c'],
        Benchmarks.MCF.value:       ['inp.in'],
        Benchmarks.CACTUS.value:    ['spec_ref.par'],
        Benchmarks.PAREST.value:    ['ref.prm'],
        Benchmarks.POVRAY.value:    ['SPEC-benchmark-ref.ini'],
        Benchmarks.OMNETPP.value:   ['omnetpp.ini'],
        Benchmarks.XALAN.value:     ['t5.xml', 'xalanc.xsl'],
        Benchmarks.X264.value:      ['BuckBunny.yuv'],
        Benchmarks.BLENDER.value:   ['sh3_no_char.blend'],
        Benchmarks.DEEPSJENG.value: ['ref.txt'],
        Benchmarks.LEELA.value:     ['ref.sgf'],
        Benchmarks.XZ.value:        ['../../all/input/cld.tar.xz']
      }
    # - Files consumed when piped from stdin
    STDIN_FILES = {
        Benchmarks.BWAVES.value:    'bwaves_1.in',
        Benchmarks.ROMS.value:      'ocean_benchmark2.in.x',
      }
    # - Files which contain command line arguments
    ARGS_FILES  = {
        Benchmarks.PERL.value:      'checkspam.in',
        Benchmarks.NAMD.value:      'namd.in',
        Benchmarks.LBM.value:       'lbm.in',
        Benchmarks.NAB.value:       'control',
        Benchmarks.EXCHANGE2.value: 'control',
    }
    # - Commands to run before we can execute the benchmark. Can also return
    #   arguments.
    @staticmethod
    def _povray_setup(b, i, d):
        shutil.copy('{}/{}/{}/input/SPEC-benchmark-ref.pov'.format(d, b, i),
                    './SPEC-benchmark-ref.pov')
        return [ '+L{}/{}/all/input'.format(d, b) ]

    @staticmethod
    def _wrf_setup(b, i, d):
        from glob import glob
        shutil.copy('{}/{}/{}/input/namelist.input'.format(d, b, i),
                    './namelist.input')
        for f in glob('{}/{}/all/input/*'.format(d, b)):
            shutil.copy(f, '.')

    def _x264_setup(self, b, i, d):
        from subprocess import run, DEVNULL
        real_input = Path(d) / b / i / 'input' / 'BuckBunny.yuv'
        if not real_input.exists():
            unprocessed_input = Path(d) / b / i / 'input' / 'BuckBunny.264'
            decode_bin  = self.bin_dir / 'ldecod_r'
            decode_args = [ str(decode_bin),
                            '-p', 'InputFile={}'.format(str(unprocessed_input)),
                            '-p', 'OutputFile={}'.format(str(real_input)) ]
            proc = run(decode_args, stdout=DEVNULL, stderr=DEVNULL)
            if proc.returncode != 0:
                raise Exception('Could not decode input file')
        return ['1280x720']

    @staticmethod
    def _cam4_setup(b, i, d):
        input_dir  = Path(d) / b / i / 'input'
        common_dir = Path(d) / b / 'all' / 'input'
        assert input_dir.exists() and common_dir.exists()
        all_files  = itertools.chain(input_dir.iterdir(), common_dir.iterdir())
        for fp in all_files:
            shutil.copy(str(fp), '.')

    @staticmethod
    def _imagick_setup(b, i, d):
        input_file = Path(d) / b / i / 'input' / 'refrate_input.tga'
        assert input_file.exists()
        shutil.copy(str(input_file), '.')
        return ['refrate_convert.out', 'refrate_convert.err', '-limit', 'disk',
                '0', 'refrate_input.tga', '-edge', '41', '-resample', '181%',
                '-emboss', '31', '-colorspace', 'YUV', '-mean-shift',
                '19x19+15%', '-resize', '3', '0%', 'refrate_output.tga']

    @staticmethod
    def _fotonik3d_setup(b, i, d):
        input_dir = Path(d) / b / i / 'input'
        assert input_dir.exists()
        for f in input_dir.iterdir():
            if '.xz' in f.name:
                os.system('xz -d -k {}'.format(str(f)))
                new_file = Path(str(f).replace('.xz', ''))
                if not (Path('.') / new_file.name).exists():
                  shutil.move(str(new_file), '.')
            elif not (Path('.') / f.name).exists():
                shutil.copy(str(f), '.')

    SETUP_FNS   = {
        Benchmarks.NAMD.value:      lambda _, b, i, d: shutil.copy(
          '{}/{}/all/input/apoa1.input'.format(d, b), './apoa1.input'),
        Benchmarks.POVRAY.value:    lambda _, b, i, d: Spec2017Bench._povray_setup(b, i, d),
        Benchmarks.LBM.value:       lambda _, b, i, d: shutil.copy(
          '{}/{}/{}/input/100_100_130_ldc.of'.format(d, b, i), './100_100_130_ldc.of'),
        Benchmarks.OMNETPP.value:   lambda _, b, i, d: shutil.copytree(
          '{}/{}/all/input/ned'.format(d, b),
          '{}/{}/{}/input/ned'.format(d, b, i))
            if not (Path(d) / b / i / 'input/ned').exists() else None,
        Benchmarks.WRF.value:       lambda _, b, i, d: Spec2017Bench._wrf_setup(b, i, d),
        Benchmarks.X264.value:      lambda obj, b, i, d: obj._x264_setup(b, i, d),
        Benchmarks.BLENDER.value:   lambda *_, **__: ['--background',
            '--render-frame', '1', '--render-output', '.'],
        Benchmarks.CAM4.value:      lambda _, b, i, d: Spec2017Bench._cam4_setup(b, i, d),
        Benchmarks.IMAGICK.value:   lambda _, b, i, d: Spec2017Bench._imagick_setup(b, i, d),
        Benchmarks.NAB.value:       lambda _, b, i, d: shutil.copytree(
            '{}/{}/{}/input/1am0'.format(d, b, i), './1am0') \
            if not Path('./1am0').exists() else None,
        Benchmarks.EXCHANGE2.value: lambda _, b, i, d: shutil.copy(
          '{}/{}/all/input/puzzles.txt'.format(d, b), './puzzles.txt'),
        Benchmarks.FOTONIK3D.value: lambda _, b, i, d: Spec2017Bench._fotonik3d_setup(b, i, d),
        Benchmarks.ROMS.value:      lambda _, b, i, d: shutil.copy(
          '{}/{}/all/input/varinfo.dat'.format(d, b), '.'),
        Benchmarks.XZ.value:        lambda *_, **__: [ '216.3MiB',
            ('19cf30ae51eddcbefda78dd06014b4b96281456e078ca7c13e1c0c9e6aaea8df'
            'f3efb4ad6b0456697718cede6bd5454852652806a657bb56e07d61128434b474'),
            '160', '59,796,407', '61,004,416', '6']
      }
    # - Used for script-like benchmarks that link with other scripts
    LIB_DIR     = {
        Benchmarks.PERL.value:   'lib',
      }
    # - All other arguments that are static
    MISC_ARGS   = {
        Benchmarks.GCC.value: [
          '-O3', '-fselective-scheduling', '-fselective-scheduling2' ],
        Benchmarks.X264.value: [ '--crf', '0', '-o', 'x264.out' ],
      }

    def __init__(self, bin_dir, input_dir, lib_dir=Path('./lib')):
        assert isinstance(bin_dir, Path)
        assert isinstance(input_dir, Path)
        assert isinstance(lib_dir, Path)
        self.bin_dir   = bin_dir
        self.input_dir = input_dir / 'spec2017'
        self.lib_dir   = lib_dir / 'spec2017'

    def _get_input_file_args(self, bench_name, input_type):
        if bench_name not in self.__class__.INPUT_FILES:
            return []
        input_file_args = []
        input_file_names = self.__class__.INPUT_FILES[bench_name]
        parent_dir = self.input_dir / bench_name / input_type / 'input'

        for infile in input_file_names:
            input_path = parent_dir / infile
            assert input_path.exists()
            input_file_args += [str(input_path.resolve())]

        return input_file_args

    def _get_stdin_args(self, bench_name, input_type):
        if bench_name not in Spec2017Bench.STDIN_FILES:
            return []
        stdin_file_name = Spec2017Bench.STDIN_FILES[bench_name]
        stdin_path = self.input_dir / bench_name / input_type / 'input' / stdin_file_name
        assert stdin_path.exists()
        return [ '<', str(stdin_path) ]

    def _get_cmdline_args(self, bench_name, input_type):
        if bench_name not in self.__class__.ARGS_FILES:
            return []
        args_file_name = self.__class__.ARGS_FILES[bench_name]
        args_file_path = self.input_dir / bench_name / input_type / 'input' / args_file_name
        assert args_file_path.exists()
        with args_file_path.open() as f:
            lines = f.readlines()
            args_raw = lines[-1].strip().replace('\t', ' ')
            return args_raw.split(' ')

    def _get_lib_args(self, bench_name):
        if bench_name not in self.__class__.LIB_DIR:
            return []
        lib_dir_name = self.__class__.LIB_DIR[bench_name]
        lib_dir_path = self.lib_dir / bench_name / lib_dir_name
        assert lib_dir_path.exists()
        return ['-I', str(lib_dir_path)]

    def _get_misc_args(self, bench_name):
        if bench_name not in self.__class__.MISC_ARGS:
            return []
        return self.__class__.MISC_ARGS[bench_name]

    def _get_setup_fn_args(self, bench_name, input_type):
        fn = lambda *_, **__: None
        if bench_name in self.__class__.SETUP_FNS:
            fn = self.__class__.SETUP_FNS[bench_name]
        maybe_args = fn(self, bench_name, input_type, self.input_dir)
        if isinstance(maybe_args, list):
            return maybe_args
        return []

    def _get_bin_path(self, bench_name):
        bin_name = Spec2017Bench.BIN_NAMES[bench_name]
        bin_path = self.bin_dir / bin_name
        assert bin_path.exists()
        return bin_path

    def create(self, bench_name, input_type):
        assert bench_name in Spec2017Bench.BENCHMARKS
        assert input_type in Spec2017Bench.INPUT_TYPES
        bin_path = self._get_bin_path(bench_name)

        setup_args   = self._get_setup_fn_args(bench_name, input_type)
        input_args   = self._get_input_file_args(bench_name, input_type)
        lib_args     = self._get_lib_args(bench_name)
        misc_args    = self._get_misc_args(bench_name)
        stdin_args   = self._get_stdin_args(bench_name, input_type)
        cmdline_args = self._get_cmdline_args(bench_name, input_type)

        args = lib_args + misc_args + input_args + cmdline_args + stdin_args + setup_args
        print(str(bin_path) + ' ' +  ' '.join(args))
        return Benchmark(bin_path, args)


class SpecBench:
    SPEC2017 = 'spec2017'
    SPEC2006 = 'spec2006'
    SUITES   = {SPEC2006: Spec2006Bench, SPEC2017: Spec2017Bench}

    def __init__(self, bin_dir=Path('bin'), input_dir=Path('data')):
        self.bin_dir = bin_dir
        self.input_dir = input_dir

    def create(self, suite_name, bench_name, input_type):
        assert suite_name in SpecBench.SUITES
        specsuite = SpecBench.SUITES[suite_name](self.bin_dir, self.input_dir)
        return specsuite.create(bench_name, input_type)

    class ParseBenchmarkNames(Action):
        def __init__(self, option_strings, dest, nargs='+', **kwargs):
            super().__init__(option_strings, dest, nargs=nargs, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            all_possible = defaultdict(list)
            for value in values:
                for suite, cls in SpecBench.SUITES.items():
                    for benchmark in cls.BENCHMARKS:
                        if value in benchmark:
                            all_possible[suite] += [benchmark]

            setattr(namespace, self.dest, all_possible)

    @classmethod
    def add_parser_args(cls, parser):
        parser.add_argument('--bench', action=cls.ParseBenchmarkNames,
                            help='Run a benchmark(s) from SPEC', nargs='+')
        parser.add_argument('--suite',
                            help='Which SPEC suite to use. Default is 2017',
                            default='spec2017', nargs='?')
        parser.add_argument('--input-type',
                            help='Which SPEC input type to use. Default is refrate',
                            default='refrate', nargs='?')
        parser.add_argument('--list-bench',
                            help='List which benchmarks are available for what suite and exit',
                            action='store_true', default=False)
        parser.add_argument('--list-suite',
                            help='List what suites are available and exit',
                            action='store_true', default=False)

    @classmethod
    def get_benchmarks(cls, args):
        if len(args.bench) == 0:
            raise Exception('No benchmarks match specified option.')
        if len(args.bench[args.suite]) == 0:
            raise Exception('No such benchmark in specified suite!')
        return args.bench[args.suite]

    @classmethod
    def maybe_display_spec_info(cls, parsed_args):
        if parsed_args.list_suite:
            pprint(cls.SUITES.keys())
            exit(0)

        if parsed_args.list_bench:
            if parsed_args.suite is None:
                raise Exception('Suite not defined!')
            if parsed_args.suite not in cls.SUITES:
                raise Exception('{} is not a valid suite!')
            pprint(cls.SUITES[parsed_args.suite].BENCHMARKS)
            exit(0)

