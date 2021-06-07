#!/bin/bash

infile='Compound.EarlyUsers.AccountType.csv'
outfile='Compound.EarlyUsers.Direct.csv'
head -1 $infile > $outfile
grep 'EOA' $infile >> $outfile
