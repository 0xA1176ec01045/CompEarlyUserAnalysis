import pandas as pd
from sys import argv

# Produce a list of addresses and proposed COMP distributions
pctSocial  = 0 # Change this variable to distribute a percentage of COMP equally across all early users
pctCapital = 100-pctSocial
interestFile = 'TotalUSDInterestByAddress.csv'
propFile = 'NewProposal.'+str(pctSocial)+'-'+str(pctCapital)+'.csv'

v1interestfile = 'CompoundV1.EarlyUserUSDInterest.csv'
v2interestfile = 'CompoundV2.EarlyUserUSDInterest.csv'
v1interest = pd.read_csv(v1interestfile)
v2interest = pd.read_csv(v2interestfile)

# Combine V1 and V2 interest for addresses that appear in both datasets
interestData = pd.concat([v1interest,v2interest],ignore_index=True).reindex()
interestData = interestData.groupby(['address'],as_index=False).sum()

# Compute total interest and write to csv (rounded to nearest 0.01 USD)
interestData['Total'] = interestData.sum(axis='columns')
interestData[['address','Total']].round(decimals=2).sort_values(['Total']).to_csv(interestFile,index=False)

# Express users' interest as a fraction of total early user interest mediated by the protocol
totalInterest = interestData['Total'].sum()
interestData['Fractional'] = interestData['Total']/totalInterest

# Express users' interest relative to a fixed percentage of the total supply (suggested value is 5%)
totalCOMPsupply = 1.e7
allocatedCOMPpct = 5
allocatedCOMP = allocatedCOMPpct*(totalCOMPsupply/100.)
interestData['x_interest'] = interestData['Fractional']*allocatedCOMP

# Exclude Compound Deployer and burn addresses:
# 0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6 Compound Deployer
CompDeployer = '0xA7ff0d561cd15eD525e31bbe0aF3fE34ac2059F6' 
BurnAddress  = '0x0000000000000000000000000000000000000000' 
interestData = interestData[interestData['address'] != CompDeployer]
interestData = interestData[interestData['address'] != BurnAddress]
#
# Exclude addresses that funded or received funds from Sybil attack addresses:
SybilFunder1   = '0xB67e217f9B39427bf2d6B3DC1aA9C03b24EAb95A'
SybilFunder2   = '0x63F4Df4b50417482e8BED4A8975249d620e7332a' # funded SybilFunder1
SybilFunder3   = '0xbac13cED7ED12E24d34ea253611214264dB1f7d3' # funded SybilFunder1
SybilFunder4   = '0x944F03520b0ECEA3375a4e8377FD998270811bB5' # funded SybilFunder1
SybilReceiver1 = '0xa9B6d40E0eE772Ea506B41eF7458283a27464eEe' # funded by SybilFunder1
SybilReceiver2 = '0xf0C42858E7CF6264c132BE7090D9D0c137c5016b' # funded by SybilFunder1
# Exclude addresses funded by SybilFunder 1 for the Sybil attack that were missed
# by a simple 5-tx filter due to the attacker reusing these addresses for other activity
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
interestData = interestData[interestData['address'] != SybilFunder1]
interestData = interestData[interestData['address'] != SybilFunder2]
interestData = interestData[interestData['address'] != SybilFunder3]
interestData = interestData[interestData['address'] != SybilFunder4]
interestData = interestData[interestData['address'] != SybilReceiver1]
interestData = interestData[interestData['address'] != SybilReceiver2]
interestData = interestData[interestData['address'] != SybilReceiver3]
interestData = interestData[interestData['address'] != SybilReceiver4]
interestData = interestData[interestData['address'] != SybilReceiver5]
interestData = interestData[interestData['address'] != SybilReceiver6]
interestData = interestData[interestData['address'] != SybilReceiver7]
interestData = interestData[interestData['address'] != SybilReceiver8]
interestData = interestData[interestData['address'] != SybilReceiver9]
interestData = interestData[interestData['address'] != SybilReceiver10]
interestData = interestData[interestData['address'] != SybilReceiver11]
interestData = interestData[interestData['address'] != SybilReceiver12]

interestData[['address','Total']].round(decimals=2).sort_values(['Total']).to_csv(interestFile,index=False)

# Translate multipliers into proposed COMP distribution
# --> Based on forum discussion of 5% distribution to early users
# --> 5% of 10M tokens = 500000 COMP to be distributed
# --> pctSocial of distribution is socialized, pctCapital is capital-time weighted
TotalCOMPdistribution = 5.e5
num_addresses = interestData.shape[0]

COMPdistribution = []
for index, row in interestData.iterrows():
    socCOMP = TotalCOMPdistribution/num_addresses
    capCOMP = row['x_interest']
    COMPdistribution.append(0.01*(pctSocial*socCOMP + pctCapital*capCOMP))
interestData['COMP'] = COMPdistribution
proposalData = interestData[['address','COMP']]
proposalData.sort_values('COMP').to_csv(propFile,index=False)
