#!/bin/bash

# Run the Compound early user analysis
python CompoundEarlyUsers.py
python CompoundV1.USDinterest.py
python CompoundV2.USDinterest.py
# Optionally, produce a simple proposal (ex. 49% social 51% capital)
python MakeProposal.py 49 51

# If the community agrees to honor request from @CryptoCraig 
# who proactively reached out about lost keys to an early user wallet
# (see evidence provided in retroactive airdrop forum thread)
sed -i s/0xe84d25b1C4fe0E5A9bEe95934AB24C9867Aac2cc/0x7d355f8b12d15213e3C6b187Cb5ca348EcD725f8/ TotalUSDInterestByAddress.csv
