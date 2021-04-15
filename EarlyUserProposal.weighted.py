import pandas as pd
from sys import argv

# Produce a list of addresses and proposed COMP distributions
# 
# Arguments:
# (1) percent weight allocated to a socialized distribution
#     (integer between 0 and 100 inclusive),
#     with the remaining percent weight allocated to a
#     (capital)*(time)-weighted distribution
#
# Requirements:
# --> run CompoundEarlyUsers.py to produce early user lists
# --> run DetectContracts.py to add "address type"
#     (external owned account or contract) to early user lists
# The two steps above are separated out because of the large
# number of RPCs necessary for the contract detection step
# --> Decide how to handle contract addresses:
# ----> FindContractCallers.py replaces contracts with the
#       EOA that initiated the contract call
# ----> But that EOA may or may not be the end user,
#       depending on how the contract is set up
# --> For this analysis, we only consider direct interactions
#     with the Compound protocol (skip contract addresses)
# 
# Assumptions:
# --> output from the steps above is stored in earlyUserFile
# --> capital weights are hard-coded in here as computed
#       by SimpleCapWeights.py

pctSocial  = int(argv[1])
pctCapital = 100-pctSocial

earlyUserFile = 'Compound.EarlyUsers.Direct.clean.csv'
proposalFile = 'Proposal.'+str(pctSocial)+'-'+str(pctCapital)+'.tvl.csv'
txData = pd.read_csv(earlyUserFile)

# Exclude all dust protocol interactions,
# where dust thresholds are defined by token as shown
dust = {  'ZRX' : 1.00, 'BAT' : 1.00, 'REP' : 1.00,
          'WETH': 0.01, 'SAI' : 1.00, 'ETH' : 0.01,
          'USDC': 1.00, 'WBTC': 0.001,'DAI' : 1.00
}
nondustDataByToken = []
for token in dust:
    FilterTxData = txData[txData['token'] == token]
    FilterTxData = FilterTxData[FilterTxData['amount'] >= dust[token]]
    nondustDataByToken.append(FilterTxData)
addressData = pd.concat(nondustDataByToken)
#print("after removing dust-scale transactions:")
#print(addressData)

CompV1deployBlock      = 6400278
EarlyUserCutoffBlock   = 10228172

# ...sort address data by address and then by block
addressData = addressData.sort_values(['address','block'])

cap_weights = { 'ZRX' : 0.506366856012202,
               'BAT' : 0.19272837890186123,
               'REP' : 14.271295633796559,
               'WETH': 225.80843211718437,
               'SAI' : 1.0,
               'ETH' : 225.80843211718437,
               'USDC': 1.0,
               'WBTC': 7893.636226132308,
               'DAI' : 1.0
}
# ...compute contribution to capital*time multiplier by tx
#    * TVL multiplier 'm' gives greater weight to earlier
#      interactions with the protocol
#    * TVL multiplier grows linearly from 1 to tvl_factor=85,
#      which is the estimated multiple by which the protocol's
#      TVL grew during the eligibility window
# m = 1 + tvl_factor(interaction_block - EarlyUserCutoffBlock)/
#                   (CompV1deployBlock - EarlyUserCutoffBlock)
#    * In case of multiple interactions by a single address,
#      we use the earliest interaction to compute the multiplier
#    * Capital multiplier 'cap' is the estimated USD value of
#      the supply/borrow action.
# cap = amount*cap_weight
#    * cap_weight is the simple two-point average of the token
#      price in USD at CompV1deployBlock and at COMPlaunchBlock
#    * See SimpleCapitalWeights.py for implementation details
captime = []
for index, row in addressData.iterrows():
    if row['action'] == 'supply' or row['action'] == 'borrow':
        cap = row['amount']*cap_weights[row['token']]
    else:
        cap = 0.0
    interaction_block = row['block']
    tvl_factor = 85
    m = 1.0 + tvl_factor*(interaction_block - EarlyUserCutoffBlock
            )/(CompV1deployBlock - EarlyUserCutoffBlock)
    captime.append(cap*m)
addressData['x_captime'] = captime

# ...sum contributions over txs to get final x_captime;
x_captime  = addressData.groupby(['address'])['x_captime'].sum()

x_captime.to_csv('x_captime.csv',index=False)
uniqueAddresses = pd.concat([x_captime],axis=1).reset_index()
print(uniqueAddresses)
 
# Exclude Compound Deployer address:
# 0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6 Compound Deployer
CompDeployer = '0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6' 
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != CompDeployer]

# Exclude addresses that funded or received funds from Sybil attack addresses:
SybilFunder1   = '0xB67e217f9B39427bf2d6B3DC1aA9C03b24EAb95A'
SybilFunder2   = '0x63F4Df4b50417482e8BED4A8975249d620e7332a' # funded SybilFunder1
SybilFunder3   = '0xbac13cED7ED12E24d34ea253611214264dB1f7d3' # funded SybilFunder1
SybilFunder4   = '0x944F03520b0ECEA3375a4e8377FD998270811bB5' # funded SybilFunder1
SybilReceiver1 = '0xa9B6d40E0eE772Ea506B41eF7458283a27464eEe' # funded by SybilFunder1
SybilReceiver2 = '0xf0C42858E7CF6264c132BE7090D9D0c137c5016b' # funded by SybilFunder1
# Exclude addresses funded by SybilFunder 1 for the Sybil attack that were missed
# by my 5-tx filter due to the attacker reusing these addresses for other activity
SybilReceiver3 = '0x4D21dc68132166c4ceE2C495BC76cc8926568fEE' # 5-tx filter missed
SybilReceiver4 = '0x61F38ed0eeaB67349099DD7bD95fE847F7F6e59c' # 5-tx filter missed
SybilReceiver5 = '0x192Bc5a28b5256f40B2Da0964dAcba3C5Aa7feF1' # 5-tx filter missed
SybilReceiver6 = '0x05987e113C74b4B1F82fd6254A2E1E7E99042D89' # 5-tx filter missed
SybilReceiver7 = '0xEe4B3CC342390484dCC2f3F65Caa971c91f82982' # 5-tx filter missed
SybilReceiver8 = '0x63F4Df4b50417482e8BED4A8975249d620e7332a' # 5-tx filter missed
SybilReceiver9 = '0xbac13cED7ED12E24d34ea253611214264dB1f7d3' # 5-tx filter missed
SybilReceiver10 ='0x944F03520b0ECEA3375a4e8377FD998270811bB5' # 5-tx filter missed
SybilReceiver11 ='0x1836d38784A7a8b7D62278d8AE59a13c2B3bED4A' # 5-tx filter missed
SybilReceiver12 ='0xEEB87F7418Df5d62D77905370cee3eC3500952f5' # 5-tx filter missed
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilFunder1]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilFunder2]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilFunder3]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilFunder4]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver1]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver2]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver3]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver4]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver5]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver6]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver7]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver8]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver9]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver10]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver11]
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != SybilReceiver12]

# Translate multipliers into proposed COMP distribution
# --> Based on forum discussion of 5% distribution to early users
# --> 5% of 10M tokens = 500000 COMP to be distributed
# --> pctSocial of distribution is socialized, pctCapital is capital-time weighted
# --> Proposed formula for distribution to user i 
#     COMP_i = pctSocial*socialCOMP_i + pctCapital*capitalWeightedCOMP_i
#     : socialCOMP_i = (Total)/(number of eligible addresses)
#     : capitalWeightedCOMP_i = (Total)*(x_captime_i)/
#                               (sum over eligible users of (x_captime))
TotalCOMPdistribution = 500000.
num_addresses = uniqueAddresses.shape[0]

sum_xcaptime = 0
for index, row in uniqueAddresses.iterrows():
    sum_xcaptime += row['x_captime']
COMPdistribution = []
for index, row in uniqueAddresses.iterrows():
    socCOMP = TotalCOMPdistribution/num_addresses
    capCOMP = TotalCOMPdistribution*row['x_captime']/sum_xcaptime
    COMPdistribution.append(0.01*(pctSocial*socCOMP + pctCapital*capCOMP))
uniqueAddresses['COMP'] = COMPdistribution
uniqueAddresses = uniqueAddresses.drop(columns=['x_captime'])
uniqueAddresses.sort_values('COMP').to_csv(proposalFile,index=False)
