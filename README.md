# Lapidary: creating beautiful gem5 simulations.

Lapidary is a tool we have built to enable more efficient [gem5][gem5] simulations. 

Lapidary works by creating gem5 checkpoints on bare-metal to avoid the
weeks of simulation required to create viable checkpoints. This is done by taking 
core dumps of the program through gdb (along with gathering some other miscellaneous process state information) and transforming the output into a gem5-compatible 
checkpoint. Lapidary can then perform short simulations over many checkpoints
(in accordance with the [SMARTS sampling methodology][smarts]) in order to 
produce statistically significant performance measurements.

For more information about Lapidary and its inception, please refer to our [blog post][blog].

## Installation

To install Lapidary:

```shell
# Clone repository
$ git clone https://github.com/efeslab/lapidary.git ./lapidary_repo
# Setup virtual environment
$ python3 -m venv virt_env
$ source virt_env/bin/activate
# install
$ pip3 install ./lapidary_repo
```

**Note**: due to some [limitations](#current-limitations), it might be necessary to run 
Lapidary in a VM with certain processor features disabled. See the [limitations section](#current-limitations) for details.

## Usage

There are two steps when running Lapidary: (1) creating checkpoints and (2) simulating checkpoints.

### Configuration

All configurations must comply with the [configuration schema][schema-file]. The file is assumed to be `./.lapidary.yaml`, but can be specified explicitly by the
`-c <PATH>` option available for all verbs.

#### Examples

1. Display the schema format and exit:

```shell
$ python3 -m lapidary --config-help
```

2. A basic configuration (all you need to run basic simulations):

`./.lapidary.yaml`:
```yaml
gem5_path: path/to/gem5/relative/to/config/file/location
```

3. Creating a FlagConfigure custom class for enabling custom features during
simulations. If you gate custom microarchitectural features behind debug flags,
you can enable them inside of FlagConfigure class, either before simulation
starts (`before_init`) or after warmup but before performance is measured
(`after_warmup`). The default config is `empty`, which enables no flags.

`./.lapidary.yaml`:
```yaml
...
gem5_flag_config_plugin: ./example_configurations.py
...
```

`./example_configurations.py`
```python
from lapidary.config import FlagConfigure

class TestConfig(FlagConfigure):
    @staticmethod
    def before_init(system):
        ...
        
    @staticmethod
    def after_warmup():
        import m5
        m5.debug.flags["..."].enable()
        ...
```

A full example configuration file is available in [our testing directory][example-config].

### Checkpoint Creation

The `create` verb is used to create checkpoints. This can either be done in 
an automated fashion (every N seconds or every M instructions) or interactively through a shell interface.

#### Examples

1. Print help:

```shell
$ python3 -m lapidary create --help
# If ./.lapidary.yaml doesn't exist
$ python3 -m lapidary -c ./lapidary_repo/.lapidary.yaml create --help
```

2. Create checkpoints for an arbitrary binary every second:

```shell
$ python3 -m lapidary create --cmd "..." --interval 1
```

3. Create checkpoints for SPEC-CPU 2017 benchmarks (requires valid configuration path) and save them to `/mnt/storage` rather than the current working directory:

```shell
$ python3 -m lapidary create --bench mcf --interval 5 --directory /mnt/storage
```

4. Create checkpoints interactively:

```shell
$ python3 -m lapidary create --cmd "..." --breakpoints ...
```

At each breakpoint, the user will be allowed to interact with the gdb process.
```
User-defined breakpoint reached. Type "help" for help from this shell, or "gdb help" for traditional help from gdb.
(py-gdb) help

Documented commands (type help <topic>):
========================================
checkpoint  exit  gdb  help  quit

(py-gdb) 
```

### Single Simulation

The `simulate` verb is used to simulate a single checkpoint that was previously
created from the `create` command. This command is useful for debugging issues with custom modifications to the gem5 simulator.

#### Examples

1. Simulate a single checkpoint from an arbitrary binary:

```shell
$ python3 -m lapidary simulate --start-checkpoint \
    test_gdb_checkpoints/0_check.cpt --binary ./test/bin/test
```

2. Simulate a single checkpoint from an arbitrary command (with arguments):

```shell
$ python3 -m lapidary simulate --start-checkpoint \
    test_gdb_checkpoints/0_check.cpt --binary ./test/bin/test --args ... 
```

3. Debug gem5 on a particular checkpoint:

```shell
$ python3 -m lapidary simulate --start-checkpoint \
    test_gdb_checkpoints/0_check.cpt --binary ./test/bin/test --args ... \
    --debug-mode
```

`--debug-mode` will not only use `gem5.debug` instead of `gem5.opt`, but it will
also runs gem5 through gdb.

4. Display loaded FlagConfigurations and simulate using a custom configuration.

```shell
$ python3 -m lapidary simulate --list-configs

['empty', 'testconfig']

$ python3 -m lapidary simulate --start-checkpoint \
    test_gdb_checkpoints/0_check.cpt --bin ./test/bin/test \
    --flag-config testconfig
```

### Parallel Simulation

The `parallel-simulate` verb is used to simulate a group of checkpoints from a 
single benchmark at once. This can be used to generate statistical performance
measurements using the [SMARTS methology][smarts]. 

This works by simulating each checkpoint for a small number of instructions in two different periods; there is a warmup period (default 5,000,000 instructions) which allows the caches to be filled, and a real simulation period (by default 100,000 instructions) which generates the reported statistics. For more details on the theory behind this sampling methodology, please refer to the [ISCA publication][smarts].

#### Examples

1. Simulate all checkpoints taken from an arbitrary command (This will look for 
checkpoints within `./test_gdb_checkpoints/`, e.g. 
`./test_gdb_checkpoints/0_check.cpt`, `./test_gdb_checkpoints/1_check.cpt`, 
etc.):

```shell
$ python3 -m lapidary parallel-simulate --binary ./test/bin/test --args ... 
```


2. Simulate all checkpoints taken from the MCF benchmark with a non-standard
checkpoint directory:

```shell
$ python3 -m lapidary parallel-simulate --bench mcf --checkpoint-dir /mnt/storage
```

### Reporting

The `report` verb is used to aggregate the results from multiple simulations
into a single report file and display them in a variety of ways. The first 
step is always to generate the aggregated report (via the `report process`
facility), then the data can be further processed into more digestable formats.

Currently we have two sub-commands:
- `report process`, to create the aggregated report.
- `report filter`, to create a more terse, easily readable report.

We plan on adding a built-in graphing facility (`report graph`) soon.

#### Examples

1. Create a report after simulating checkpoints in `/mnt/storage`:

```shell
$ python3 -m lapidary report process -d /mnt/storage
```

The output is in `./report.json`, which looks like:

```json
{
    "results": {
        "benchmark_name": {
            "configuration_1": {
                "sim_insts": {
                    "mean": 103165.07692307692,
                    "std": 2507.9945546971453,
                    "ci": 1363.3613701898664,
                    "count": 13.0
                },
                ...
```

- `count` is the number of checkpoints used to generate the statistic.
- `mean` is the arithmetic mean across the checkpoints.
- `std` is the standard deviation, and `ci` is the 95% confidence interval.

2. Create a summary report that contains only the `cpi` (cycles per instruction)
 and `MLP` (memory-level parallelism) statistic.

 ```shell
 $ python3 -m lapidary report filter cpi -o cpi_only.yaml -i report.json
 ```

 This reads the report from `report.json` and writes the output into `cpi_only.yaml`.
 The output type can be either `yaml` or `json` (use `report filter --help` 
 for details).

 `cpi_only.yaml`:
 ```yaml
 benchmark_1:
  configuration_1:
    cpi: 0.98
  configuration_2:
    cpi: 1.1
  ...
 ```

## Current Limitations

1. Currently, gem5 does not support all Intel ISA extensions (such as AVX). Gem5 
is able to disable use of these instructions by libc when it loads programs, 
however glibc seems to dynamically check which extensions are available at runtime
and use those implementations. This causes a problem for some checkpoints, as 
they end up attempting to use AVX instructions in gem5, causing a crash since 
gem5 does not recognize these instructions. 

    Our temporary workaround was to run our experiments in a VM, as it is easy to 
specify which extensions to disable via the `-cpu` flag in QEMU, e.g.

```bash
... -cpu host,-avx2,-bmi1,-bmi2 ...
```

2. Not all checkpoints run successfully. For example, checkpoints that attempt
to invoke syscalls generally end up crashing.

3. As we generate a lot of checkpoints for our sampling methodology, Lapidary 
quickly occupies a lot of disk space (a few hundred GB is not uncommon). 

4. Our sampling method does not support simulation over custom instructions. 
In other words, our sampling method only works when simulating existing ISAs
(which can be run on bare metal) with potentially different back-end implementations.

## Future Work

1. We are currently working on a feature for syscall tracing, i.e. replaying the 
call trace from the checkpointing process upon resuming simulation in gem5. This 
will solve many of the issues that currently cause some checkpoints to fail.

2. Add support for checkpoint "key-frames", i.e. storing small numbers of full 
checkpoints, then creating diffs from those for following checkpoints. This
feature will need to be configurable, as it will increase the processing required
for simulation startup.

3. Add support for custom instructions. This can be presented in several modes; 
either skip custom instructions during checkpoint creation, or emulate them at 
a high level when encountered. This will not catch all use cases, but I imagine 
it will catch many.

4. Add support for cloud deployments, i.e. distributed simulation, potentially
using ansible to automate provisioning/setup as well.

## Contributing

Please feel free to create forks, post issues, make pull requests, or email us directly! We appreciate 
any and all feedback and would like to make this tool as useful as possible.


[example-config]: test/lapidary.yaml
[schema-file]: config/schema.yaml
[gem5]: http://gem5.org/Main_Page
[blog]: https://medium.com/@iangneal/lapidary-crafting-more-beautiful-gem5-simulations-4bc6f6aad717
[smarts]: https://dl.acm.org/citation.cfm?id=859629
