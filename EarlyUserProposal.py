import pandas as pd

# Produce a list of addresses and proposed COMP distributions
# Requirements:
# --> run CompoundEarlyUsers.py to produce early user lists
# --> run DetectContracts.py to add "address type"
#     (external owned account or contract) to early user lists
# The two steps above are separated out because of the large
# number of RPCs necessary for the contract detection step
# 
# Assumptions:
# --> output from the steps above is stored in earlyUserFile
# --> capital weights are hard-coded in here as computed
#       by SimpleCapWeights.py
earlyUserFile = 'Compound.EarlyUsers.AccountType.csv'
proposalFile = 'Compound.EarlyUsers.Proposal.csv'
txData = pd.read_csv(earlyUserFile)

# If address is a contract, determine the requesting EOA;
# this step needs to be recursive in case of nested contract calls
contractTxData = txData[txData['addressType'] == 'contract']
while contractTxData['addressType'].str.contains('contract').any():
    for index, row in contractTxData.iterrows():
        if (row['addressType'] == 'contract'):
            # Overwrite contract address with calling address
            tx = w3.eth.getTransaction(row['txhash'])
            contractTxData.loc[index,'address'] = tx['from']
            # Update addressType if calling address is EOA
            if not isContract(tx['from']):
                contractTxData.loc[index,'addressType'] = 'EOA'

# Merge updated contract call records with direct protocol interaction records
userTxData = txData[txData['addressType'] == 'EOA']
txData = pd.concat([userTxData,contractTxData])
print("txData after replacing contracts with calling addresses:")
print(txData)

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

# Compute simplified time multiplier for each address:
# x_time = 1 + (EarlyUserCutoffBlock - earliest_interaction_block)/
#              (EarlyUserCutoffBlock - CompV1deployBlock)
# In case of multiple interactions by a single address,
# we use the earliest interaction to compute the multiplier
# --> Earliest users get x_time ~= 2; last ones in get x_time ~= 1
CompV1deployBlock      = 6400278
EarlyUserCutoffBlock   = 10228172

# ...sort address data by address and then by block
addressData = addressData.sort_values(['address','block'])

# Compute simplified capital multiplier for each address:
# x_cap = capital-weighted sum of tokens deposited and borrowed,
#         where capital_weight is the simple two-point average
#         of the token price in USD at CompV1deployBlock
#         and at COMPlaunchBlock
# --> See SimpleCapitalWeights.py for implementation details
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
# ...compute contribution to capital multiplier by token
cap = []
time = []
for index, row in addressData.iterrows():
    if row['action'] == 'supply' or row['action'] == 'borrow':
        cap.append(row['amount']*cap_weights[row['token']])
    else:
        cap.append(0.0)
    interaction_block = row['block']
    t = 1.0 + (EarlyUserCutoffBlock - interaction_block
            )/(EarlyUserCutoffBlock - CompV1deployBlock)
    time.append(t)
addressData['x_cap'] = cap
addressData['x_time'] = time
#print("addressData just before groupby():")
#print(addressData)

# ...sum contributions over tokens to get final x_cap;
# ...and take max over transactions to get final x_time
x_cap  = addressData.groupby(['address'])['x_cap'].sum()
x_time = addressData.groupby(['address'])['x_time'].max()

#print(x_cap)
#print(x_time)
x_cap.to_csv('x_cap.csv',index=False)
x_time.to_csv('x_time.csv',index=False)
uniqueAddresses = pd.concat([x_cap,x_time],axis=1).reset_index()
print(uniqueAddresses)
 
# Exclude addresses owned by the protocol:
# 0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6 Compound Deployer
# ... any others to include here?
CompDeployer = '0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6' 
uniqueAddresses = uniqueAddresses[uniqueAddresses['address'] != CompDeployer]

# Translate multipliers into proposed COMP distribution
# --> Based on forum discussion of 5% distribution to early users
# --> 5% of 10M tokens = 500000 COMP to be distributed
# --> Half of distribution is socialized, half is capital-time weighted
# --> Proposed formula for distribution to user i 
#     COMP_i = 0.5*(socialCOMP_i + capitalWeightedCOMP_i)
#     : socialCOMP_i = (500000)/(number of eligible addresses)
#     : capitalWeightedCOMP_i = (500000)*(x_cap_i)*(x_time_i)/
#                               (sum over eligible users of (x_cap)*(x_time))
TotalCOMPdistribution = 500000.
num_addresses = uniqueAddresses.shape[0]

sum_xcap_xtime = 0
for index, row in uniqueAddresses.iterrows():
    sum_xcap_xtime += row['x_cap']*row['x_time']
COMPdistribution = []
for index, row in uniqueAddresses.iterrows():
    socCOMP = TotalCOMPdistribution/num_addresses
    capCOMP = TotalCOMPdistribution*row['x_cap']*row['x_time']/sum_xcap_xtime
    COMPdistribution.append(0.5*(socCOMP + capCOMP))
uniqueAddresses['COMP'] = COMPdistribution

uniqueAddresses.to_csv(proposalFile,index=False)
