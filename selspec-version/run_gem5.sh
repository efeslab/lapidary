#! /bin/bash

TEST=mcf_r
BIN=bin/$TEST
DATA="data/spec2017/505.mcf_r/test/input/inp.in"
N=0
CHK=gdb/check_gdb_$N.cpt
W=5000000
R=50000000

echo "Single O3 + Cooldown"
time ./Experiment.py --binary $BIN --args $DATA --start-checkpoint $CHK \
  --warmup-insts $W --reportable-insts $R --enable-patch \
  --output-dir gem5/"$TEST"_check_"$N"_cooldown/

exit

echo "Single O3 + Cooldown"
./Experiment.py --binary $BIN --args $DATA --start-checkpoint $CHK \
  --warmup-insts $W --reportable-insts $R --enable-patch \
  --output-dir gem5/"$TEST"_check_"$N"_cooldown/

exit

echo "Single O3"
./Experiment.py --binary $BIN --args $DATA --start-checkpoint $CHK \
  --warmup-insts $W --reportable-insts $R \
  --output-dir gem5/"$TEST"_check_"$N"_o3/

echo "In order"
./Experiment.py --binary $BIN --args $DATA --start-checkpoint $CHK \
  --warmup-insts $W --reportable-insts $R --timing-cpu \
  --output-dir gem5/"$TEST"_check_"$N"_inorder/

exit

echo "Parallel"
./Parallel.py

echo "Full Run O3"
./Experiment.py --binary $BIN --args $DATA \
  --warmup-insts $W --reportable-insts -1

echo "Full Run In Order"
./Experiment.py --binary $BIN --args $DATA \
  --warmup-insts $W --reportable-insts -1 --timing-cpu

exit

./Experiment.py --binary bin/mcf_r --args data/spec2017/505.mcf_r/test/input/inp.in \
  --start-checkpoint gdb/check_gdb_0.cpt --timing-cpu

sudo perf stat -e instructions,cycles bin/mcf_r \
 data/spec2017/505.mcf_r/test/input/inp.in
