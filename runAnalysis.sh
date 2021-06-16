#!/bin/bash

# Run the Compound early user analysis
python CompoundEarlyUsers.py
python CompoundV1.USDinterest.py
python CompoundV2.USDinterest.py
# Optionally, produce a simple proposal (ex. 49% social 51% capital)
python MakeProposal.py 49 51
