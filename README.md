# Lapidary: creating beautiful gem5 simulations.

Lapidary is a tool we have built to enable more efficient [gem5][gem5] simulations.
In short, Lapidary works by creating gem5 checkpoints on bare-metal to avoid the
weeks of simulation required to create viable checkpoints. 

For more information about Lapidary and it's inception, please refer to our [blog posts][blog].

## Installation

To install Lapidary:

```shell
# Clone repository
git clone https://github.com/efeslab/lapidary.git
# Setup virtual environment
python3 -m venv virt_env
source virt_env/bin/activate
# install
pip3 install ./lapidary
```

**Note**: due to some [limitations](#limitations), it might be necessary to run 
Lapidary in a VM with certain processor features disabled. See the [limitations section](#limitations) for details.

## Usage

There are two steps when running Lapidary: (1) creating checkpoints and (2) simulating checkpoints.

### Configuration

All configurations must comply with the [configuration schema][schema-file]. The file is assumed to be `./lapidary.yaml`, but can be specified explicitly by the
`-c <PATH>` option available for all verbs.

#### Examples

1. Display the schema format and exit:

```shell
python3 -m lapidary --config-help
```

2. A basic configuration (all you need to run basic):
```yaml
gem5_path: path/to/gem5/relative/to/config/file/location
```

A full example configuration file is available in [our testing directory][example-config].

### Checkpoint Creation

The `create` verb is used to create checkpoints. This can either be done in 
an automated fashion (every N seconds or every M instructions) or interactively through a shell interface.

#### Examples

1. Print help:

```shell
python3 -m lapidary create --help
```

2. Create checkpoints for an arbitrary binary every second:

```shell
python3 -m lapidary create --cmd "..." --interval 1
```

3. Create checkpoints for SPEC-CPU 2017 benchmarks (requires valid configuration path):

```shell
python3 -m lapidary create --bench mcf --interval 5 --directory /mnt/storage
```

4. Create checkpoints interactively:

```shell
python3 -m lapidary create --cmd "..." --breakpoints ...
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
created from the `create` command. This command is more useful for debugging
gem5 simulations.

#### Examples

1. Simulate a single checkpoint from an arbitrary binary:

```shell
python3 -m lapidary simulate --start-checkpoint test_gdb_
checkpoints/0_check.cpt --binary ./test/bin/test
```

2. Simulate a single checkpoint from an arbitrary command (with arguments):

```shell
python3 -m lapidary simulate --start-checkpoint test_gdb_
checkpoints/0_check.cpt --binary ./test/bin/test --args ... 
```

3. Debug gem5 on a particular checkpoint:

```shell
python3 -m lapidary simulate --start-checkpoint test_gdb_
checkpoints/0_check.cpt --binary ./test/bin/test --args ... --debug-mode
```

`--debug-mode` will not only use `gem5.debug` instead of `gem5.opt`, but it will
also runs gem5 through gdb.

### Parallel Simulation

The `parallel-simulate` verb is used to simulate a group of checkpoints from a 
single benchmark at once.

#### Examples

1. Simulate all checkpoints taken from the MCF benchmark:

```shell
python3 -m lapidary parallel-simulate --bench mcf --checkpoint-dir /mnt/storage
```

## Current Limitations

1. Currently, gem5 does not support all Intel ISA extentions (such as AVX). Gem5 
is able to disable use of these instructions by libc when it loads programs, 
however glibc seems to dynamically check which extentions are available at runtime
and use those implementations. This causes a problem for some checkpoints, as 
they end up attempting to use AVX instructions in gem5, causing a crash since 
gem5 does not recognize these instructions. 

Our temporary workaround was to run our experiments in a VM, as it is easy to 
specify which extentions to disable via the `-cpu` flag in QEMU, e.g.

```bash
... -cpu host,-avx2,-bmi1,-bmi2 ...
```

2. As we generate a lot of checkpoints for our sampling methodology, Lapidary 
quickly occupies a lot of disk space (a few hundred GB is not uncommon). 

3. Our sampling method does not support simulation over custom instructions. 
In other words, our sampling method only works when simulating existing ISAs
(which can be run on bare metal) with potentially different backend implementations.

## Future Work

1. Add support for checkpoint "keyframes", i.e. storing small numbers of full 
checkpoints, then creating diffs from those for following checkpoints. This
feature will need to be configurable, as it will increase the processing required
for simulation startup.

2. Add support for custom instructions. This can be presented in several modes; either skip custom instructions during checkpoint creation, or emulate them at a high level when encountered. This will not catch all use cases, but I imagine it
will catch many.

3. Add support for cloud deployments, i.e. distributed simulation.

## Contributing

Fork, post issues, make pull requests, whatever floats your boat! We appreciate 
any and all feedback.

[example-config]: test/lapidary.yaml
[schema-file]: config/schema.yaml
[gem5]: http://gem5.org/Main_Page
[blog]: https://medium.com/@iangneal/lapidary-crafting-more-beautiful-gem5-simulations-4bc6f6aad717