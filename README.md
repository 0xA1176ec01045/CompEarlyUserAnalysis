# CompEarlyUserAnalysis

The Compound community is considering the merits of a retroactive airdrop to early users. The active discussion can be found on the [Compound forum](https://www.comp.xyz/t/should-compound-retroactively-airdrop-tokens-to-early-users/595).

This repository uses the Python web3 module and Compound contract application binary interfaces (ABIs) to:
* `CompoundEarlyUsers.py`: identify addresses that interacted in specified ways with the Compound protocol prior to the introduction of the COMP token
* `DetectContracts.py`: identify which of these addresses are contracts and which are external owned accounts (EOAs)
* `EarlyUserProposal.weighted.py`: generate a proposed distribution of COMP to early users that includes a socialized part and a capital-weighted part

## Structure of the distribution

The COMP proposed for a qualifying address (indexed by *i*) is a sum of two terms,

`TotalCOMP_i = w*socialCOMP_i + (1-w)*capitalCOMP_i`
<img src="https://render.githubusercontent.com/render/math?math=\mathrm{TotalCOMP}_i = w \left(\mathrm{socialCOMP}\right)_i+\left(1-w\right)\left(\mathrm{capitalCOMP}\right)_i">

This tool is developed by a small-fry early Compound user who uses Python for scientific computing but is not a professional Solidity or web3 developer. Please be kind, constructive criticism, suggestions, and pull requests are all welcome!
