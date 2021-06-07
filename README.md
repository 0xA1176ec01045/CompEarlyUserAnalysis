# CompEarlyUserAnalysis

The Compound community is considering the merits of a retroactive airdrop to early users. The active discussion can be found on the [Compound forum](https://www.comp.xyz/t/should-compound-retroactively-airdrop-tokens-to-early-users/595).

This repository uses the Python web3 module; Compound contract application binary interfaces (ABIs); Compound MarketHistory API; and price history data from CoinGecko to:
* `CompoundEarlyUsers.py`: identify addresses that interacted in specified ways with V1 and V2 of the Compound protocol prior to the introduction of the COMP token
* `DetectContracts.py`: identify which of these addresses are contracts and which are external owned accounts (EOAs)
* CompoundV1.USDinterest.py: calculate the total supply and borrow interest accrued by each address in V1 of the Compound protocol prior to the announcement of the COMP token
* CompoundV2.USDinterest.py: calculate the total supply and borrow interest accrued by each address in V2 of the Compound protocol prior to the announcement of the COMP token
* `EarlyUserProposal.weighted.py`: generate a proposed distribution of COMP to early users that may include:
  * a socialized component, where all addresses receive the same fixed amount of COMP
  * a capital-weighted component, where each address receives an amount of COMP proportional to its capital-at-risk in the protocol as measured by total supply and borrow interest accrued prior to the announcement of the COMP token

## Structure of the `verion_1` distribution

Strictly for historical reference, a high-level overview of how `version_1` of this tool computes a proposed COMP distribution by early-user address is provided in the file [summary.pdf](https://github.com/0xA1176ec01045/CompEarlyUserAnalysis/blob/main/proposals/version_1/summary.pdf).

The development of this tool and analysis is generously sponsored by a grant from the [Compound Grants program](https://compoundgrants.org). This tool is developed by an early Compound user who uses Python for scientific computing but is not a professional Solidity or web3 developer. Constructive criticism, suggestions, and pull requests are all welcome!
