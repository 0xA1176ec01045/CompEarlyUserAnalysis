import web3
import pandas as pd
from etherscan_py import etherscan_py
from time import sleep

earlyUserFile = 'Compound.EarlyUsers.Direct.csv'
txData = pd.read_csv(earlyUserFile)

# Flag addresses that meet the criteria for being
# likely participants in the sybil attack on V1
# stablecoin voting:
# --> Address supplied <= 0.03 WETH to Compound between
#     blocks 6579469 and 6658725
# ----> 6579469 is approx first block on pub date
#       of Medium article announcing the vote
# ----> 6658725 is approx block height at the
#       time the vote closed
# --> Address has no other interactions with the
#     protocol before or after the flagged one
# --> Address has a transaction history of five
#     or fewer total transactions according to Etherscan
#    (this last one ensures we don't accidentally
#     ensnare a user whose only interaction with the
#     protocol happened at precisely the wrong time)
#
# This will miss a few known Sybil addresses because
# some of them were reused later by the attacker
# (exceeding the 5 tx threshold);
# these are directly excluded in the MakeProposal script

minBlock = 6579469
maxBlock = 6658725
flaggableTxs = []
votingPeriodData = txData[txData['block'] >= minBlock]
votingPeriodData = votingPeriodData[votingPeriodData['block'] <= maxBlock]
for index, row in votingPeriodData.iterrows():
    if     row['action'] == 'supply' \
       and row['token']  == 'WETH'   \
       and row['amount'] <= 0.03:
        flaggableTxs.append('flagged')
    else:
        flaggableTxs.append('clean')
votingPeriodData['status'] = flaggableTxs
flaggedAddresses = votingPeriodData[votingPeriodData['status'] == 'flagged']['address'].tolist()

removelist = []
for address in flaggedAddresses:
    flaggedAddressHistory = txData[txData['address'] == address]['txhash'].tolist()
    count = len(flaggedAddressHistory)
    print('Address ' + str(address) + ' interacted with the protocol ' + str(count) + ' times')
    if count == 1:
        # Use etherscan to check whether address has 5 or fewer total transactions;
        # this step should ensure we only capture addresses generated
        # exclusively for the Sybil attack
        es = etherscan_py.Client('YOUR-API-KEY')
        tx_count = len(es.get_all_transactions(address,1))
        sleep(5)
        if (tx_count > 5):
            print('Address ' + str(address) + ' has ' + str(tx_count) + ' total txs, retained')
        if (tx_count <= 5):
            removelist.append(address)
            print('Address ' + str(address) + ' has ' + str(tx_count) + ' total txs, REMOVED')

# Remove transactions from removelisted addresses from tx data
cleanTxData = txData.copy()
for index, row in txData.iterrows():
    if row['address'] in removelist:
        cleanTxData.drop(index,inplace=True)
    
cleanUserFile = 'Compound.EarlyUsers.Direct.noSybil.csv'
cleanTxData.to_csv(cleanUserFile,index=False)
