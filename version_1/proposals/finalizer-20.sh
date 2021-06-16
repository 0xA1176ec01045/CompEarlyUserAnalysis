#!/bin/bash

infile=$1
targetminCOMP=20
minimumCOMP=$(tail -n +2 $infile | head -1 | cut -d\, -f2)
topup=$(echo "$targetminCOMP-$minimumCOMP" | bc -l)
awk -F ',' -v t=$topup '(NR>1){printf "%s%24.18g\n",$1,($2+t)}' $infile
