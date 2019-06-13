#! /bin/bash

IN="data/spec2017/505.mcf_r/test/input/inp.in"
ARGS="bin/mcf_r.gem5 $IN"

set -e

make spec2017

gdb --batch -ex "set \$args = \"$ARGS\"" -x GDBProcess.py

