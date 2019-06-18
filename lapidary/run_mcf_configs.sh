#! /bin/bash

./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByNumBlockedBranches_5 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByNumBlockedBranches_6 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByNumBlockedBranches_7 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByNumBlockedBranches_8 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByNumBlockedBranches_9 -n 200

./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_5 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_10 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_20 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_40 -n 200
./ParallelSim.py --bench mcf -d /mnt/storage2/mcf_r_gdb_checkpoints --cooldown-config BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_80 -n 200
