# CompEarlyUserAnalysis

The Compound community is considering the merits of a retroactive airdrop to early users. The active discussion can be found on the [Compound forum](https://www.comp.xyz/t/should-compound-retroactively-airdrop-tokens-to-early-users/595).

This repository uses the Python web3 module; Compound contract application binary interfaces (ABIs); Compound MarketHistory API; and price history data from CoinGecko to:
* `CompoundEarlyUsers.py`: identify addresses that interacted in specified ways with V1 and V2 of the Compound protocol prior to the introduction of the COMP token
* `DetectContracts.py`: identify which of these addresses are contracts and which are external owned accounts (EOAs)
* `CompoundV1.USDinterest.py`: calculate the total supply and borrow interest accrued by each address in V1 of the Compound protocol prior to the announcement of the COMP token
* `CompoundV2.USDinterest.py`: calculate the total supply and borrow interest accrued by each address in V2 of the Compound protocol prior to the announcement of the COMP token
* `MakeSimpleProposal.py`: generate a proposed distribution of COMP to early users that may include:
  * a socialized component, where all addresses receive the same fixed amount of COMP
  * a capital-weighted component, where each address receives an amount of COMP proportional to its capital-at-risk in the protocol as measured by total supply and borrow interest accrued prior to the announcement of the COMP token

## How to use this tool

Interested parties can use the scripts provided here to verify accrued USD-denominated interest by address in `CompoundV1.EarlyUserUSDinterest.csv` and `CompoundV2.EarlyUserUSDInterest.csv`, including review of all underlying calculations. Here's how:

### Configuration:
* Clone this repository: from your CLI, `git clone https://github.com/0xA1176ec01045/CompEarlyUserAnalysis.git`
* Check that your environment has Python3 installed (for example, check the output of `python --version`) with the following modules available: `pandas`, `web3`, `json`, `requests`, `datetime`, `time`, `sys`.  Use `pip install` or your preferred method for installing module dependencies if any are missing.
* Configuration for pulling on-chain data:
  * Decide whether you will use your own local ethereum node for inter-process communications (IPCs) or make remote procedure calls (RPCs) to an endpoint provided by a third party (typically a paid service, though some offer free trial or starter accounts).
  * Replace the line specifying the RPC endpoint in each Python script with the endpoint provided by your RPC provider. If using IPC, replace the call to `Web3.HTTPProvider()` with `Web3.IPCProvider()` and specify the full path to your IPC pipe.

### Generating your own `NewProposal*.csv`:
* Run the bash script `runAnalysis.sh` which performs all necessary steps in sequence.

or, run the steps separately:

* Run `python CompoundEarlyUsers.py` to (re)produce the lists `CompoundV1.EarlyUserEvents.csv` and `CompoundV2.EarlyUserEvents.csv`. These lists comprise a history of all interactions with V1 and V2 of the protocol, respectively. Unfortunately for this analysis (but probably fortunately for us as consumers of gas on ethereum!), accrued interest is not directly recorded in the contract events emitted during these transactions; however, they provide sufficient information to compute accrued interest as follows.
* Run `python CompoundV1.USDinterest.py` and `python CompoundV2.USDinterest.py` to (re)produce the lists `CompoundV1.EarlyUserUSDInterest.csv` and `CompoundV2.EarlyUserUSDInterest.csv`. These scripts produce a tally of USD-denominated interest accrued for each asset on each version of the protocol during the early user period.
* Run `python MakeSimpleProposal.py a b` to produce a list of early-user addresses and the amount of COMP they would receive if, of an initial 500,000 COMP total apportioned to early users, `a`% is distributed equally across all addresses and `100-a`% is distributed according to interest accrued during the early user period (`b` is not actually used by the script). Note that the conversion of accrued interest to USD is performed at the time interest was accrued; as asset prices fluctuate, it is expected that total USD-denominated interest will not match the present-day USD value of accrued interest as denominated in the original assets. The approach used here is consistent with the spirit of using total supply and borrow interest accrued over time as a proxy for capital at risk over time in the protocol.

## Absence of a suggested distribution model

The `CompEarlyUserAnalysis` tool is now focused squarely on providing *data* for Compound governance to discuss the optimal structuring of an early user distribution. Therefore, the tool does not deliver a suggested or recommended distribution model. Likewise, the tool offers governance a means of handling contract-based interactions differently from EOAs but does not enforce or make a recommendation regarding treatment of contract-based interactions.

## Structure of the obsolete `version_1` distribution model

Strictly for historical reference, a high-level overview of how the now-obsolete `version_1` of this tool computed a proposed COMP distribution by early-user address is provided in the file [summary.pdf](https://github.com/0xA1176ec01045/CompEarlyUserAnalysis/blob/main/version_1/proposals/summary.pdf).

## Acknowledgments / About This Project
The development of this tool and analysis is generously sponsored by a grant from the [Compound Grants program](https://compoundgrants.org) to an early Compound user. Constructive criticism, suggestions, and pull requests are all welcome!
