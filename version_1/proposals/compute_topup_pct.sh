#!/bin/bash

# Computes the percentage by which the proposed 500,000 COMP
# distribution to early users would need to be inflated 
# to set the floor for distributions at exactly 20 COMP

ProposalCSV=$1
COMPproposed=500000
COMPrequired=$(awk 'BEGIN{s=0}{s+=$2}END{print s}' $ProposalCSV)
TopUpPercent=$(echo "100*($COMPrequired/$COMPproposed-1.0)" | bc -l)
printf "%4.1f\n" $TopUpPercent
