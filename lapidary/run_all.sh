#! /bin/bash

DIR=/mnt/storage2

BENCHMARKS="500.perlbench_r,perlbench_r 502.gcc_r,cpugcc_r 503.bwaves_r,bwaves_r 505.mcf_r,mcf_r 507.cactuBSSN_r,cactucBSSN_r 508.namd_r,namd_r 510.parest_r,parest_r 511.povray_r,povray_r 519.lbm_r,519.lbm_r 520.omnetpp_r,omnetpp_r 521.wrf_r,wrf_r 523.xalancbmk_r,cpuxalan_r 531.deepsjeng_r,deepsjeng_r"

for b in $BENCHMARKS; do
  IFS=","
  set -- $b
  if [ -d "$DIR/$2_gdb_checkpoints" ]; then
    echo "Skipping checkpoint generation for $1"
  else
    echo "Checkpointing for $1"
    ./GDBProcess.py --bench $1 --directory $DIR
    sync
  fi

  ls simulation_results/$1_* > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "Skipping simulation for $1, already have results!"
  else
    ./ParallelSim.py --bench $1 -d $DIR/$2_gdb_checkpoints --config-group grand -n 300
    sync
  fi
done

