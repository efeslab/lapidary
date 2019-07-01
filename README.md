# Lapidary: creating beautiful gem5 simulations.

Please refer to 

## Installation

```shell
# Clone repository
git clone https://github.com/efeslab/lapidary.git
# Setup virtual environment
python3 -m venv virt_env
source virt_env/bin/activate
# install
pip3 install ./lapidary
```

## Usage

### Configuration

All configurations must comply with the [configuration schema][schema-file].

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

The `create` verb is used to create checkpoints.

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
python3 -m lapidary create --bench mcf --interval 5
```

### Single Simulation

The `simulate` verb is used to simulate a single checkpoint that was previously
created from the `create` command. This command is more useful for debugging
gem5 simulations.

#### Examples

1. 

### Parallel Simulation

The `parallel-simulate` verb is used to simulate a group of checkpoints from a 
single benchmark at once.

#### Examples

1. Simulate all checkpoints taken from the MCF benchmark:

```shell

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

[example-config]: test/lapidary.yaml
[schema-file]: config/schema.yaml