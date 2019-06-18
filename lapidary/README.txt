Here's the flow:

- GDBProcess.py -- create the raw checkpoints
- CheckpointConvert.py -- create gem5-readable checkpoints from the gdb dumps
- Experiment.py / Parallel.py -- run gem5 on the checkpoints
- Results.py -- parse the results into a nice report.
